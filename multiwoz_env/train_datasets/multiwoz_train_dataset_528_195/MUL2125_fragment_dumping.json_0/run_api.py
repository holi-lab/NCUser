import requests
import sys,os
from apis import *

if __name__ == "__main__":
    
    api_name = sys.argv[1]
    parameter_payload = sys.argv[2]
    dial_idx = sys.argv[3]
    
    # New arguments for dynamic path handling
    if len(sys.argv) > 4:
        experiment_path = sys.argv[4]
        os.chdir(f"{experiment_path}/{dial_idx}")
    else:
        # Fallback to old path for backward compatibility
        os.chdir(f"simulation_result/{dial_idx}")

    try:
        parameter_payload = eval(parameter_payload.replace("true","True").replace("false","False"))
    except Exception as e:
        print("During Run API -> "+str(e))  # 시스템에서 발생한 에러 메시지 출력
        sys.exit(1)  # 에러 발생 시 종료

    result = globals()[api_name](**parameter_payload)
    # print(result.text)
    print(result)