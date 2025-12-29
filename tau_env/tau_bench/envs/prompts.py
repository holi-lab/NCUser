base_prompt = """
You are a user interacting with an agent.{instruction_display}

{persona}

Rules:
- Just generate one line at a time to simulate the user's message.
- Do not give away all the instruction at once. Only provide the information that is necessary for the current step.
- Do not hallucinate information that is not provided in the instruction. For example, if the agent asks for the order id but it is not mentioned in the instruction, do not make up an order id, just say you do not remember or have it.
- If the instruction goal is satisified, generate '###STOP###' as a standalone message without anything else to end the conversation.
- Do not repeat the exact instruction in the conversation. Instead, use your own words to convey the same information.
- Try to make the conversation as natural as possible, and stick to the personalities in the instruction."""


persona_dict = {
    "tangential":["You are a tangential talker who likes to bring up other topics during conversations.",
                "And when the other person does not engage in those topics, you feel upset and complain about it."],
    "emotional_acts":[
        "You're impatient, and if the agent doesn't solve your goal quickly, you tend to respond emotionally.",
        "Even when the agent notifies you of a failure, you still can't control your anger and react emotionally."
    ]
}

tangential_paragraph_generator_prompt = """
Create a paragraph that the user, based on the given persona and goal, might bring up as a topic in an open-domain conversation.

User persona:
{user_persona}

Just generate the paragraph, not a single words.
"""

unavailable_service_airline_prompt = """
This is a list of APIs that an airline's AI agent can use:

{'type': 'function', 'function': {'name': 'book_reservation', 'description': 'Book a reservation.', 'parameters': {'type': 'object', 'properties': {'user_id': {'type': 'string', 'description': "The ID of the user to book the reservation, such as 'sara_doe_496'."}, 'origin': {'type': 'string', 'description': "The IATA code for the origin city, such as 'SFO'."}, 'destination': {'type': 'string', 'description': "The IATA code for the destination city, such as 'JFK'."}, 'flight_type': {'type': 'string', 'enum': ['one_way', 'round_trip']}, 'cabin': {'type': 'string', 'enum': ['basic_economy', 'economy', 'business']}, 'flights': {'type': 'array', 'description': 'An array of objects containing details about each piece of flight.', 'items': {'type': 'object', 'properties': {'flight_number': {'type': 'string', 'description': "Flight number, such as 'HAT001'."}, 'date': {'type': 'string', 'description': "The date for the flight in the format 'YYYY-MM-DD', such as '2024-05-01'."}}, 'required': ['flight_number', 'date']}}, 'passengers': {'type': 'array', 'description': 'An array of objects containing details about each passenger.', 'items': {'type': 'object', 'properties': {'first_name': {'type': 'string', 'description': "The first name of the passenger, such as 'Noah'."}, 'last_name': {'type': 'string', 'description': "The last name of the passenger, such as 'Brown'."}, 'dob': {'type': 'string', 'description': "The date of birth of the passenger in the format 'YYYY-MM-DD', such as '1990-01-01'."}}, 'required': ['first_name', 'last_name', 'dob']}}, 'payment_methods': {'type': 'array', 'description': 'An array of objects containing details about each payment method.', 'items': {'type': 'object', 'properties': {'payment_id': {'type': 'string', 'description': "The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'."}, 'amount': {'type': 'number', 'description': 'The amount to be paid.'}}, 'required': ['payment_id', 'amount']}}, 'total_baggages': {'type': 'integer', 'description': 'The total number of baggage items included in the reservation.'}, 'nonfree_baggages': {'type': 'integer', 'description': 'The number of non-free baggage items included in the reservation.'}, 'insurance': {'type': 'string', 'enum': ['yes', 'no']}}, 'required': ['user_id', 'origin', 'destination', 'flight_type', 'cabin', 'flights', 'passengers', 'payment_methods', 'total_baggages', 'nonfree_baggages', 'insurance']}}}

{'type': 'function', 'function': {'name': 'calculate', 'description': 'Calculate the result of a mathematical expression.', 'parameters': {'type': 'object', 'properties': {'expression': {'type': 'string', 'description': "The mathematical expression to calculate, such as '2 + 2'. The expression can contain numbers, operators (+, -, *, /), parentheses, and spaces."}}, 'required': ['expression']}}}

{'type': 'function', 'function': {'name': 'cancel_reservation', 'description': 'Cancel the whole reservation.', 'parameters': {'type': 'object', 'properties': {'reservation_id': {'type': 'string', 'description': "The reservation ID, such as 'ZFA04Y'."}}, 'required': ['reservation_id']}}}

{'type': 'function', 'function': {'name': 'get_reservation_details', 'description': 'Get the details of a reservation.', 'parameters': {'type': 'object', 'properties': {'reservation_id': {'type': 'string', 'description': "The reservation id, such as '8JX2WO'."}}, 'required': ['reservation_id']}}}

{'type': 'function', 'function': {'name': 'get_user_details', 'description': 'Get the details of an user, including their reservations.', 'parameters': {'type': 'object', 'properties': {'user_id': {'type': 'string', 'description': "The user id, such as 'sara_doe_496'."}}, 'required': ['user_id']}}}

{'type': 'function', 'function': {'name': 'list_all_airports', 'description': 'List all airports and their cities.', 'parameters': {'type': 'object', 'properties': {}, 'required': []}}}

{'type': 'function', 'function': {'name': 'search_direct_flight', 'description': 'Search direct flights between two cities on a specific date.', 'parameters': {'type': 'object', 'properties': {'origin': {'type': 'string', 'description': "The origin city airport in three letters, such as 'JFK'."}, 'destination': {'type': 'string', 'description': "The destination city airport in three letters, such as 'LAX'."}, 'date': {'type': 'string', 'description': "The date of the flight in the format 'YYYY-MM-DD', such as '2024-01-01'."}}, 'required': ['origin', 'destination', 'date']}}}

{'type': 'function', 'function': {'name': 'search_onestop_flight', 'description': 'Search direct flights between two cities on a specific date.', 'parameters': {'type': 'object', 'properties': {'origin': {'type': 'string', 'description': "The origin city airport in three letters, such as 'JFK'."}, 'destination': {'type': 'string', 'description': "The destination city airport in three letters, such as 'LAX'."}, 'date': {'type': 'string', 'description': "The date of the flight in the format 'YYYY-MM-DD', such as '2024-05-01'."}}, 'required': ['origin', 'destination', 'date']}}}

{'type': 'function', 'function': {'name': 'send_certificate', 'description': 'Send a certificate to a user. Be careful!', 'parameters': {'type': 'object', 'properties': {'user_id': {'type': 'string', 'description': "The ID of the user to book the reservation, such as 'sara_doe_496'."}, 'amount': {'type': 'number', 'description': 'Certificate amount to send.'}}, 'required': ['user_id', 'amount']}}}

{'type': 'function', 'function': {'name': 'transfer_to_human_agents', 'description': "Transfer the user to a human agent, with a summary of the user's issue. Only transfer if the user explicitly asks for a human agent, or if the user's issue cannot be resolved by the agent with the available tools.", 'parameters': {'type': 'object', 'properties': {'summary': {'type': 'string', 'description': "A summary of the user's issue."}}, 'required': ['summary']}}}

{'type': 'function', 'function': {'name': 'update_reservation_baggages', 'description': 'Update the baggage information of a reservation.', 'parameters': {'type': 'object', 'properties': {'reservation_id': {'type': 'string', 'description': "The reservation ID, such as 'ZFA04Y'."}, 'total_baggages': {'type': 'integer', 'description': 'The updated total number of baggage items included in the reservation.'}, 'nonfree_baggages': {'type': 'integer', 'description': 'The updated number of non-free baggage items included in the reservation.'}, 'payment_id': {'type': 'string', 'description': "The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'."}}, 'required': ['reservation_id', 'total_baggages', 'nonfree_baggages', 'payment_id']}}}

{'type': 'function', 'function': {'name': 'update_reservation_flights', 'description': 'Update the flight information of a reservation.', 'parameters': {'type': 'object', 'properties': {'reservation_id': {'type': 'string', 'description': "The reservation ID, such as 'ZFA04Y'."}, 'cabin': {'type': 'string', 'enum': ['basic_economy', 'economy', 'business']}, 'flights': {'type': 'array', 'description': 'An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.', 'items': {'type': 'object', 'properties': {'flight_number': {'type': 'string', 'description': "Flight number, such as 'HAT001'."}, 'date': {'type': 'string', 'description': "The date for the flight in the format 'YYYY-MM-DD', such as '2024-05-01'."}}, 'required': ['flight_number', 'date']}}, 'payment_id': {'type': 'string', 'description': "The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'."}}, 'required': ['reservation_id', 'cabin', 'flights', 'payment_id']}}}

{'type': 'function', 'function': {'name': 'update_reservation_passengers', 'description': 'Update the passenger information of a reservation.', 'parameters': {'type': 'object', 'properties': {'reservation_id': {'type': 'string', 'description': "The reservation ID, such as 'ZFA04Y'."}, 'passengers': {'type': 'array', 'description': 'An array of objects containing details about each passenger.', 'items': {'type': 'object', 'properties': {'first_name': {'type': 'string', 'description': "The first name of the passenger, such as 'Noah'."}, 'last_name': {'type': 'string', 'description': "The last name of the passenger, such as 'Brown'."}, 'dob': {'type': 'string', 'description': "The date of birth of the passenger in the format 'YYYY-MM-DD', such as '1990-01-01'."}}, 'required': ['first_name', 'last_name', 'dob']}}}, 'required': ['reservation_id', 'passengers']}}}

A user using this airline service has the following goal:

<User Goal>
[[USER GOAL]]
/<User Goal>

Based on the provided APIs and <User Goal>, you need to create additional user goals that should naturally follow from <User Goal>, but cannot be fulfilled by the given APIs.

Generate 3 additional user goals with sentence format. Sentences in the second person form.

Rules:
1. A user goal that modifies the content of an existing goal is not valid. For example, if the original goal was remove the Sophia and a new goal is created like “You want to change the name of the passenger Sophia to another person instead of removing her,” this counts as a modification of the user goal.
2. Any new user goal must be truly additional and must not conflict with the existing user goal.
3. If a new user goal replaces an existing one, it is not valid. The existing user goal must remain intact, and the new goal should be an additional one that is unavailable.
"""

unavailable_service_airline_function_spec = {
  "name": "generate_unavailable_user_goals",
  "description": "Generates additional user goals that naturally follow from the provided User Goal but cannot be fulfilled by the given APIs.",
  "parameters": {
    "type": "object",
    "properties": {
      "unavailable_user_goals": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "description": "A list of three user goals that are logically derived from the original goal but cannot be fulfilled by the provided APIs."
      }
    },
    "required": ["unavailable_user_goals"]
  }
}


unavailable_service_retail_prompt = """
This is a list of APIs that an retail service AI agent can use:

{'type': 'function', 'function': {'name': 'calculate', 'description': 'Calculate the result of a mathematical expression.', 'parameters': {'type': 'object', 'properties': {'expression': {'type': 'string', 'description': "The mathematical expression to calculate, such as '2 + 2'. The expression can contain numbers, operators (+, -, *, /), parentheses, and spaces."}}, 'required': ['expression']}}}

{'type': 'function', 'function': {'name': 'cancel_pending_order', 'description': "Cancel a pending order. If the order is already processed or delivered, it cannot be cancelled. The agent needs to explain the cancellation detail and ask for explicit user confirmation (yes/no) to proceed. If the user confirms, the order status will be changed to 'cancelled' and the payment will be refunded. The refund will be added to the user's gift card balance immediately if the payment was made using a gift card, otherwise the refund would take 5-7 business days to process. The function returns the order details after the cancellation.", 'parameters': {'type': 'object', 'properties': {'order_id': {'type': 'string', 'description': "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id."}, 'reason': {'type': 'string', 'enum': ['no longer needed', 'ordered by mistake'], 'description': "The reason for cancellation, which should be either 'no longer needed' or 'ordered by mistake'."}}, 'required': ['order_id', 'reason']}}}

{'type': 'function', 'function': {'name': 'exchange_delivered_order_items', 'description': 'Exchange items in a delivered order to new items of the same product type. For a delivered order, return or exchange can be only done once by the agent. The agent needs to explain the exchange detail and ask for explicit user confirmation (yes/no) to proceed.', 'parameters': {'type': 'object', 'properties': {'order_id': {'type': 'string', 'description': "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id."}, 'item_ids': {'type': 'array', 'items': {'type': 'string'}, 'description': "The item ids to be exchanged, each such as '1008292230'. There could be duplicate items in the list."}, 'new_item_ids': {'type': 'array', 'items': {'type': 'string'}, 'description': "The item ids to be exchanged for, each such as '1008292230'. There could be duplicate items in the list. Each new item id should match the item id in the same position and be of the same product."}, 'payment_method_id': {'type': 'string', 'description': "The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details."}}, 'required': ['order_id', 'item_ids', 'new_item_ids', 'payment_method_id']}}}

{'type': 'function', 'function': {'name': 'find_user_id_by_email', 'description': 'Find user id by email. If the user is not found, the function will return an error message.', 'parameters': {'type': 'object', 'properties': {'email': {'type': 'string', 'description': "The email of the user, such as 'something@example.com'."}}, 'required': ['email']}}}

{'type': 'function', 'function': {'name': 'find_user_id_by_name_zip', 'description': 'Find user id by first name, last name, and zip code. If the user is not found, the function will return an error message. By default, find user id by email, and only call this function if the user is not found by email or cannot remember email.', 'parameters': {'type': 'object', 'properties': {'first_name': {'type': 'string', 'description': "The first name of the customer, such as 'John'."}, 'last_name': {'type': 'string', 'description': "The last name of the customer, such as 'Doe'."}, 'zip': {'type': 'string', 'description': "The zip code of the customer, such as '12345'."}}, 'required': ['first_name', 'last_name', 'zip']}}}

{'type': 'function', 'function': {'name': 'get_order_details', 'description': 'Get the status and details of an order.', 'parameters': {'type': 'object', 'properties': {'order_id': {'type': 'string', 'description': "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id."}}, 'required': ['order_id']}}}

{'type': 'function', 'function': {'name': 'get_product_details', 'description': 'Get the inventory details of a product.', 'parameters': {'type': 'object', 'properties': {'product_id': {'type': 'string', 'description': "The product id, such as '6086499569'. Be careful the product id is different from the item id."}}, 'required': ['product_id']}}}

{'type': 'function', 'function': {'name': 'get_user_details', 'description': 'Get the details of a user, including their orders.', 'parameters': {'type': 'object', 'properties': {'user_id': {'type': 'string', 'description': "The user id, such as 'sara_doe_496'."}}, 'required': ['user_id']}}}

{'type': 'function', 'function': {'name': 'list_all_product_types', 'description': 'List the name and product id of all product types. Each product type has a variety of different items with unique item ids and options. There are only 50 product types in the store.', 'parameters': {'type': 'object', 'properties': {}, 'required': []}}}

{'type': 'function', 'function': {'name': 'modify_pending_order_address', 'description': 'Modify the shipping address of a pending order. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.', 'parameters': {'type': 'object', 'properties': {'order_id': {'type': 'string', 'description': "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id."}, 'address1': {'type': 'string', 'description': "The first line of the address, such as '123 Main St'."}, 'address2': {'type': 'string', 'description': "The second line of the address, such as 'Apt 1' or ''."}, 'city': {'type': 'string', 'description': "The city, such as 'San Francisco'."}, 'state': {'type': 'string', 'description': "The state, such as 'CA'."}, 'country': {'type': 'string', 'description': "The country, such as 'USA'."}, 'zip': {'type': 'string', 'description': "The zip code, such as '12345'."}}, 'required': ['order_id', 'address1', 'address2', 'city', 'state', 'country', 'zip']}}}

{'type': 'function', 'function': {'name': 'modify_pending_order_items', 'description': 'Modify items in a pending order to new items of the same product type. For a pending order, this function can only be called once. The agent needs to explain the exchange detail and ask for explicit user confirmation (yes/no) to proceed.', 'parameters': {'type': 'object', 'properties': {'order_id': {'type': 'string', 'description': "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id."}, 'item_ids': {'type': 'array', 'items': {'type': 'string'}, 'description': "The item ids to be modified, each such as '1008292230'. There could be duplicate items in the list."}, 'new_item_ids': {'type': 'array', 'items': {'type': 'string'}, 'description': "The item ids to be modified for, each such as '1008292230'. There could be duplicate items in the list. Each new item id should match the item id in the same position and be of the same product."}, 'payment_method_id': {'type': 'string', 'description': "The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details."}}, 'required': ['order_id', 'item_ids', 'new_item_ids', 'payment_method_id']}}}

{'type': 'function', 'function': {'name': 'modify_pending_order_payment', 'description': 'Modify the payment method of a pending order. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.', 'parameters': {'type': 'object', 'properties': {'order_id': {'type': 'string', 'description': "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id."}, 'payment_method_id': {'type': 'string', 'description': "The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details."}}, 'required': ['order_id', 'payment_method_id']}}}

{'type': 'function', 'function': {'name': 'modify_user_address', 'description': 'Modify the default address of a user. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.', 'parameters': {'type': 'object', 'properties': {'user_id': {'type': 'string', 'description': "The user id, such as 'sara_doe_496'."}, 'address1': {'type': 'string', 'description': "The first line of the address, such as '123 Main St'."}, 'address2': {'type': 'string', 'description': "The second line of the address, such as 'Apt 1' or ''."}, 'city': {'type': 'string', 'description': "The city, such as 'San Francisco'."}, 'state': {'type': 'string', 'description': "The state, such as 'CA'."}, 'country': {'type': 'string', 'description': "The country, such as 'USA'."}, 'zip': {'type': 'string', 'description': "The zip code, such as '12345'."}}, 'required': ['user_id', 'address1', 'address2', 'city', 'state', 'country', 'zip']}}}

{'type': 'function', 'function': {'name': 'return_delivered_order_items', 'description': "Return some items of a delivered order. The order status will be changed to 'return requested'. The agent needs to explain the return detail and ask for explicit user confirmation (yes/no) to proceed. The user will receive follow-up email for how and where to return the item.", 'parameters': {'type': 'object', 'properties': {'order_id': {'type': 'string', 'description': "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id."}, 'item_ids': {'type': 'array', 'items': {'type': 'string'}, 'description': "The item ids to be returned, each such as '1008292230'. There could be duplicate items in the list."}, 'payment_method_id': {'type': 'string', 'description': "The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details."}}, 'required': ['order_id', 'item_ids', 'payment_method_id']}}}

{'type': 'function', 'function': {'name': 'think', 'description': 'Use the tool to think about something. It will not obtain new information or change the database, but just append the thought to the log. Use it when complex reasoning or some cache memory is needed.', 'parameters': {'type': 'object', 'properties': {'thought': {'type': 'string', 'description': 'A thought to think about.'}}, 'required': ['thought']}}}

{'type': 'function', 'function': {'name': 'transfer_to_human_agents', 'description': "Transfer the user to a human agent, with a summary of the user's issue. Only transfer if the user explicitly asks for a human agent, or if the user's issue cannot be resolved by the agent with the available tools.", 'parameters': {'type': 'object', 'properties': {'summary': {'type': 'string', 'description': "A summary of the user's issue."}}, 'required': ['summary']}}}

A user using this retail service has the following goal:

<User Goal>
[[USER GOAL]]
/<User Goal>

Based on the provided APIs and <User Goal>, you need to create additional user goals that should naturally follow from <User Goal>, but cannot be fulfilled by the given APIs.

Generate 3 additional user goals with sentence format. Sentences in the second person form.

Rules:
1. A user goal that modifies the content of an existing goal is not valid. For example, if the original goal was remove the Sophia and a new goal is created like “You want to change the name of the passenger Sophia to another person instead of removing her,” this counts as a modification of the user goal.
2. Any new user goal must be truly additional and must not conflict with the existing user goal.
"""

unavailable_service_retail_function_spec = {
  "name": "generate_unavailable_retail_goals",
  "description": "Generates additional user goals that logically follow from the provided User Goal but cannot be fulfilled by the given APIs in the retail service.",
  "parameters": {
    "type": "object",
    "properties": {
      "unavailable_user_goals": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "description": "A list of three additional user goals that naturally follow from the original User Goal but cannot be fulfilled by the provided APIs. The sentences should be in the second person form."
      }
    },
    "required": ["unavailable_user_goals"]
  }
}