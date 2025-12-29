
#!/usr/bin/env python3
"""
API Caller for Tau-Bench
=========================

This script allows you to call any API from the Tau-Bench airline or retail environments
by providing the API name and input parameters.

Usage:
    python api_caller.py <domain> <api_name> [parameters...]

Examples:
    python api_caller.py airline get_user_details --user_id=sara_doe_496
    python api_caller.py retail get_product_details --product_id=6086499569
    python api_caller.py airline search_direct_flight --origin=JFK --destination=LAX --date=2024-05-15
"""

import sys
import json
import argparse
from typing import Any, Dict, List, Optional

# Import the data loaders and tools
from tau_bench.envs.airline.data import load_data as load_airline_data
from tau_bench.envs.retail.data import load_data as load_retail_data
from tau_bench.envs.airline.tools import ALL_TOOLS as AIRLINE_TOOLS
from tau_bench.envs.retail.tools import ALL_TOOLS as RETAIL_TOOLS


class APICallError(Exception):
    """Custom exception for API call errors."""
    pass


class TauBenchAPICaller:
    """Main class for calling Tau-Bench APIs."""
    
    def __init__(self):
        self.airline_data = load_airline_data()
        self.retail_data = load_retail_data()
        self.airline_tools = {tool.get_info()['function']['name']: tool for tool in AIRLINE_TOOLS}
        self.retail_tools = {tool.get_info()['function']['name']: tool for tool in RETAIL_TOOLS}
    
    def list_apis(self, domain: Optional[str] = None) -> Dict[str, List[str]]:
        """List all available APIs."""
        apis = {}
        
        if domain is None or domain == 'airline':
            apis['airline'] = list(self.airline_tools.keys())
        
        if domain is None or domain == 'retail':
            apis['retail'] = list(self.retail_tools.keys())
            
        return apis
    
    def get_api_info(self, domain: str, api_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific API."""
        if domain == 'airline':
            if api_name not in self.airline_tools:
                raise APICallError(f"API '{api_name}' not found in airline domain")
            return self.airline_tools[api_name].get_info()
        elif domain == 'retail':
            if api_name not in self.retail_tools:
                raise APICallError(f"API '{api_name}' not found in retail domain")
            return self.retail_tools[api_name].get_info()
        else:
            raise APICallError(f"Unknown domain: {domain}")
    
    def call_api(self, domain: str, api_name: str, **kwargs) -> str:
        """Call a specific API with the given parameters."""
        if domain == 'airline':
            if api_name not in self.airline_tools:
                raise APICallError(f"API '{api_name}' not found in airline domain")
            tool = self.airline_tools[api_name]
            return tool.invoke(self.airline_data, **kwargs)
        elif domain == 'retail':
            if api_name not in self.retail_tools:
                raise APICallError(f"API '{api_name}' not found in retail domain")
            tool = self.retail_tools[api_name]
            return tool.invoke(self.retail_data, **kwargs)
        else:
            raise APICallError(f"Unknown domain: {domain}")
    
    def parse_parameter_value(self, param_name: str, param_value: str, param_info: Dict[str, Any]) -> Any:
        """Parse a parameter value based on its type definition."""
        param_type = param_info.get('type', 'string')
        
        if param_type == 'string':
            return param_value
        elif param_type == 'integer':
            try:
                return int(param_value)
            except ValueError:
                raise APICallError(f"Parameter '{param_name}' must be an integer")
        elif param_type == 'number':
            try:
                return float(param_value)
            except ValueError:
                raise APICallError(f"Parameter '{param_name}' must be a number")
        elif param_type == 'array':
            try:
                # Try to parse as JSON first
                return json.loads(param_value)
            except json.JSONDecodeError:
                # If not valid JSON, split by comma
                return [item.strip() for item in param_value.split(',')]
        elif param_type == 'object':
            try:
                return json.loads(param_value)
            except json.JSONDecodeError:
                raise APICallError(f"Parameter '{param_name}' must be valid JSON")
        else:
            return param_value


def main():
    parser = argparse.ArgumentParser(
        description="Call Tau-Bench APIs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('domain', choices=['airline', 'retail'], 
                       help='The domain to use (airline or retail)')
    parser.add_argument('api_name', nargs='?', help='The name of the API to call')
    parser.add_argument('--list-apis', action='store_true',
                       help='List all available APIs')
    parser.add_argument('--api-info', action='store_true',
                       help='Show detailed information about the specified API')
    parser.add_argument('--json-output', action='store_true',
                       help='Output result as pretty-printed JSON')
    
    # Parse known args first to handle dynamic parameters
    args, unknown = parser.parse_known_args()
    
    caller = TauBenchAPICaller()
    
    try:
        # Handle list APIs command
        if args.list_apis:
            apis = caller.list_apis(args.domain)
            print(f"\nAvailable APIs in {args.domain} domain:")
            for api in apis[args.domain]:
                print(f"  - {api}")
            return
        
        # Handle API info command
        if args.api_info:
            if not args.api_name:
                raise APICallError("API name is required when using --api-info")
            info = caller.get_api_info(args.domain, args.api_name)
            print(f"\nAPI Information for {args.api_name}:")
            print(f"Description: {info['function']['description']}")
            print("\nParameters:")
            properties = info['function']['parameters']['properties']
            required = info['function']['parameters'].get('required', [])
            
            for param_name, param_info in properties.items():
                required_marker = " (required)" if param_name in required else " (optional)"
                param_type = param_info.get('type', 'unknown')
                description = param_info.get('description', 'No description')
                
                print(f"  - {param_name} ({param_type}){required_marker}: {description}")
                
                if 'enum' in param_info:
                    print(f"    Allowed values: {param_info['enum']}")
            return
        
        # Parse dynamic parameters
        if not args.api_name:
            raise APICallError("API name is required")
            
        params = {}
        api_info = caller.get_api_info(args.domain, args.api_name)
        properties = api_info['function']['parameters']['properties']
        
        for param_arg in unknown:
            if param_arg.startswith('--'):
                if '=' in param_arg:
                    param_name, param_value = param_arg[2:].split('=', 1)
                else:
                    raise APICallError(f"Parameter {param_arg} must be in format --param=value")
                
                if param_name not in properties:
                    raise APICallError(f"Unknown parameter: {param_name}")
                
                params[param_name] = caller.parse_parameter_value(
                    param_name, param_value, properties[param_name]
                )
        
        # Check required parameters
        required = api_info['function']['parameters'].get('required', [])
        missing = [req for req in required if req not in params]
        if missing:
            raise APICallError(f"Missing required parameters: {missing}")
        
        # Call the API
        result = caller.call_api(args.domain, args.api_name, **params)
        
        # Output result
        if args.json_output:
            try:
                parsed_result = json.loads(result)
                print(json.dumps(parsed_result, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                print(result)
        else:
            print(result)
            
    except APICallError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()