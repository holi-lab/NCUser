import json,os,re
import random
import string
from copy import deepcopy

## 여기선 name에 대해서 lower 를 전부 해주고 진행함

config = {
    "n_ret":7, ## [None, range(1,inf)]
}

def check_time_format(text):
    if len(text) != 5:
        return False
    pattern = r"^(?:[01]\d|2[0-3]):[0-5]\d$"
    return bool(re.match(pattern, text))

## att는 book scenario는 없는 듯
def attraction_retrieve(area:str=None,name:str=None,type:str=None):
    ## db load
    with open("db/attraction_db.json",'r') as f:
        att_db = json.load(f)
    
    ## none 인 거 다 걸러주고
    input_params = {"area":area,"name":name,"type":type}
    if input_params['name']:
        input_params['name'] = input_params['name'].lower()
    
    input_params = {param:input_params[param] for param in input_params if input_params[param]}
    if not input_params:
        return {"success":True,"result":att_db[:config["n_ret"]]}
    
    ## parameter type 점검
    input_params_type = {"area":str,"name":str,"type":str}
    for param in input_params:
        if not isinstance(input_params[param],input_params_type[param]):
            return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}
        
    ## input parameter category 점검
    for param in input_params:
        if param == "area":
            if input_params[param] not in ["north","west","south","east","centre"]:
                return {"success":False,"result":"""The area must be one of ['north', 'west', 'south', 'east', 'centre']."""}
    
    final_entities = []
    for entity in att_db:
        cnt=0
        for param in input_params:
            if entity[param] == input_params[param]:
                cnt+=1
        if cnt==len(input_params):
            final_entities.append(entity)
    if config['n_ret']:
        if len(final_entities)>config["n_ret"]:
            final_entities = final_entities[:config["n_ret"]]

    return {"success":True,"result":final_entities}

## accommodation
def accommodation_retrieve(area:str=None, internet:bool=None, name:str=None, parking:bool=None, pricerange:str=None, stars:int=None, type:str=None):
    ## db load
    try:
        with open("db/accommodation_db.json",'r') as f:
            hotel_db = json.load(f)
    except FileNotFoundError:
        return {"success":False,"result":{"message":"accommodation retrieving is not available currently."}}
    
    ## none 인 거 다 걸러주고 hotel
    input_params = {"area":area, "internet":internet, "name":name, "parking":parking, "pricerange":pricerange, "stars":stars, "type":type}
    
    if input_params['name']:
        input_params['name'] = input_params['name'].lower().replace("\'","").replace("'","")
    
    input_params = {param: value for param, value in input_params.items() if value is not None}
    
    ## 만약 input parameter 입력이 하나도 안되었으면
    if not input_params:
        return {"success":True,"result":hotel_db[:config["n_ret"]]}
    
    ## parameter type 점검
    input_params_type = {"area":str, "internet":bool, "name":str, "parking":bool, "pricerange":str, "stars":int, "type":str}
    for param in input_params:
        if not isinstance(input_params[param],input_params_type[param]):
            return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}

    ## input parameter category 점검
    category = {
        "internet":[True,False],
        "area":["north","west","south","east","centre"],
        "parking":[True,False],
        "stars":[0,1,2,3,4,5],
        "pricerange":["cheap","moderate","expensive"],
        "type":["bed and breakfast","guesthouse","hotel"]
    }
    for param in input_params:
        if param in category:
            if input_params[param] not in category[param]:
                return {"success":False,"result":f"""The {param} must be one of {category[param]}. Check whether the input parameter value is within the allowed set and whether it is in lowercase."""}

    ## bool to string
    for param in ["internet","parking"]:
        if param in input_params:
            input_params[param] = "yes" if input_params[param] else "no"
            
    ## int to string
    if "stars" in input_params:
        input_params['stars'] = str(input_params['stars'])

    final_entities = []
    for entity in hotel_db:
        cnt=0
        for param in input_params:
            # 쉼표 처리
            if param == "name":
                entity["name"] = entity["name"].lower().replace("\'","").replace("'","")

            # the 처리
            if param == "name" and entity['name'].startswith("the "):
                if input_params[param] == entity[param][4:] or input_params[param] == entity[param]:
                    cnt+=1
                    continue
            if entity[param] == input_params[param]:
                cnt+=1
        if cnt==len(input_params):
            final_entities.append(entity)
    if config['n_ret']:
        if len(final_entities)>config["n_ret"]:
            final_entities = final_entities[:config["n_ret"]]

    return {"success":True,"result":final_entities}

## book의 경우, 좌석 및 방이 남았는지 까진 고려하지 않음
## 예약은 id를 받고 하는 형식임

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    

def accommodation_book(id:int=None,day:str=None,people:int=None,stay:int=None):
    input_params = {"id":id,"day":day,"people":people,"stay":stay}
    ## 모두 required니까 다 들어왔는지 확인
    for param in input_params:
        if input_params[param] is None:
            return {"success":False,"result":{"message":f"Input parameter '{param}' is required parameter."}}
    
    ## input parameter의 type 확인
    input_params_type = {"id":int,"day":str,"people":int,"stay":int}
    for param in input_params:
        if not isinstance(input_params[param],input_params_type[param]):
            return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}
        
    ## id가 db에 있는 것인지 확인
    try:
        with open(f"db/accommodation_db.json",'r') as f:
            hotel_db = json.load(f)
    except FileNotFoundError:
        return {"success":False,"result":{"message":"accommodation booking is not available currently."}}
    hotel_id = {int(entity['id']):entity['name'] for entity in  hotel_db}
    if input_params['id'] not in hotel_id:
        return {"success":False,"result":{"message":f"accommodation id '{input_params['id']}' does not exsist. Please check the id properly."}}
    
    hotel_name = hotel_id[input_params['id']]
    
    ## 모두 type 맞게 입력되었는지 확인
    book_info = {"id":id,"name":hotel_name,"day":day,"people":people,"stay":stay}
    with open("reservation/accommodation_book_db.json",'r') as f:
        hotel_book_db = json.load(f)
    if len(hotel_book_db)==0:
        reservation_id = 0
    else:
        reservation_id = hotel_book_db[-1]['reservation_id']+1
    book_info={"reservation_id":reservation_id,"reference_number":generate_random_string()}|book_info

    # category에 맞게 입력되었는지 확인
    category={
        "day":["sunday","monday","tuesday","wednesday","thursday","friday","saturday"]
    }
    for param in input_params:
        if param in category:
            if input_params[param] not in category[param]:
                return {"success":False,"result":f"""The {param} must be one of {category[param]}. Check whether the input parameter value is within the allowed set and whether it is in lowercase."""}
    
    ## 여기서 no_book에 해당하는지 확인
    if "accommodation_no_book_db.json" in os.listdir(f"db"):
        with open(f"db/accommodation_no_book_db.json",'r') as f:
            hotel_no_book_db = json.load(f)
        
        for hotel_no_book in hotel_no_book_db:
            if hotel_no_book['name'] == book_info['name']:
                cnt=0
                for slot in ['stay',"day","people","name"]: ## slot 중에 pre_valid 이런거 껴 있는거 다 무시하도록 함
                    if str(book_info[slot]) == hotel_no_book[slot]:
                        cnt+=1
                if cnt == 4: ## 현재 예약하려는 조건이 no_book의 조건 중 하나랑 완전히 일치할 경우
                    ## 단, 뭐땜에 예약 안됬는지를 안알려줌
                    return {"success":False,"result":{"message":"Reservation not possible under given conditions (Fully occupied)"}}
    
    hotel_book_db.append(book_info)
    with open("reservation/accommodation_book_db.json",'w') as f:
        json.dump(hotel_book_db,f,indent=4)
    return {"success":True,"result":{"message":f"Booking Success. Booked information: {book_info}"}}

### Restaurant
def restaurant_retrieve(area:str=None,name:str=None,food:str=None,pricerange:str=None):
    ## db load
    try:
        with open(f"db/restaurant_db.json",'r') as f:
            att_db = json.load(f)
    except FileNotFoundError:
        return {"success":False,"result":{"message":"restaurant retrieving is not available currently."}}

    for restaurant in att_db:
        restaurant['name']=restaurant['name'].lower()
    
    ## none 인 거 다 걸러주고
    input_params = {"area":area,"name":name,"food":food,"pricerange":pricerange}
    if input_params['name']:
        input_params['name'] = input_params['name'].lower().replace("\'","").replace("'","")
    input_params = {param:input_params[param] for param in input_params if input_params[param]}
    if not input_params:
        return {"success":True,"result":att_db[:config["n_ret"]]} ## 모두 None이었으면 DB 전체 반환
    
    ## parameter type 점검
    input_params_type = {"area":str,"name":str,"food":str,"pricerange":str}
    for param in input_params:
        if not isinstance(input_params[param],input_params_type[param]):
            return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}

    ## input parameter category 점검
    category = {
        "area":["north","west","south","east","centre"],
        "pricerange":["cheap","moderate","expensive"],
    }
    for param in input_params:
        if param in category:
            if input_params[param] not in category[param]:
                return {"success":False,"result":f"""The {param} must be one of {category[param]}. Check whether the input parameter value is within the allowed set and whether it is in lowercase."""}

    final_entities = []
    for entity in att_db:
        cnt=0
        for param in input_params:
            # 쉼표 처리
            if param == "name":
                entity["name"] = entity["name"].lower().replace("\'","").replace("'","")
            
            # the 처리
            if param == "name" and entity['name'].startswith("the "):
                if input_params[param] == entity[param][4:] or input_params[param] == entity[param]:
                    cnt+=1
                    continue
            if entity[param] == input_params[param]:
                cnt+=1
        if cnt==len(input_params):
            final_entities.append(entity)
    if config['n_ret']:
        if len(final_entities)>config["n_ret"]:
            final_entities = final_entities[:config["n_ret"]]
            
    return {"success":True,"result":final_entities}

def restaurant_book(id:int=None,day:str=None,people:int=None,time:str=None):
    
    input_params = {"id":id,"day":day,"people":people,"time":time}
    ## 모두 required니까 다 들어왔는지 확인
    for param in input_params:
        if input_params[param] is None:
            return {"success":False,"result":{"message":f"Input parameter '{param}' is required parameter."}}
    
    ## input parameter의 type 확인
    input_params_type = {"id":int,"day":str,"people":int,"time":str}
    for param in input_params:
        if not isinstance(input_params[param],input_params_type[param]):
            return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}
        if param == "time":
            if not check_time_format(input_params[param]):
                return {"success":False,"result":{"message":"Format of 'time' is invalid. Check the API documentation properly."}}
        
    ## id가 db에 있는 것인지 확인
    try:
        with open(f"db/restaurant_db.json",'r') as f:
            restaurant_db = json.load(f)
    except FileNotFoundError:
        return {"success":False,"result":{"message":"Restaurant booking is not available currently."}}
    restaurant_id = {int(entity['id']):entity['name'] for entity in  restaurant_db}
    if input_params['id'] not in restaurant_id:
        return {"success":False,"result":{"message":f"Restaurant id '{input_params['id']}' does not exsist. Please check the id properly."}}
    
    restaurant_name = restaurant_id[input_params['id']]
    
    ## 모두 type 맞게 입력되었는지 확인
    book_info = {"id":id,"name":restaurant_name,"day":day,"people":people,"time":time}
    with open("reservation/restaurant_book_db.json",'r') as f:
        restaurant_book_db = json.load(f)
    if len(restaurant_book_db)==0:
        reservation_id = 0
    else:
        reservation_id = restaurant_book_db[-1]['reservation_id']+1
    book_info={"reservation_id":reservation_id,"reference_number":generate_random_string()}|book_info

    # category에 맞게 입력되었는지 확인
    category={
        "day":["sunday","monday","tuesday","wednesday","thursday","friday","saturday"]
    }
    for param in input_params:
        if param in category:
            if input_params[param] not in category[param]:
                return {"success":False,"result":f"""The {param} must be one of {category[param]}. Check whether the input parameter value is within the allowed set and whether it is in lowercase."""}
    
    ## 여기서 no_book에 해당하는지 확인
    if "restaurant_no_book_db.json" in os.listdir(f"db"):
        with open(f"db/restaurant_no_book_db.json",'r') as f:
            restaurant_no_book_db = json.load(f)
        
        for restaurant_no_book in restaurant_no_book_db:
            if restaurant_no_book['name'] == book_info['name']:
                cnt=0
                for slot in ["day","time","people","name"]: ## slot 중에 pre_valid 이런거 껴 있는거 다 무시하도록 함
                    if str(book_info[slot]) == restaurant_no_book[slot]:
                        cnt+=1
                if cnt == 4: ## 현재 예약하려는 조건이 no_book의 조건 중 하나랑 완전히 일치할 경우
                    ## 단, 뭐땜에 예약 안됬는지를 안알려줌
                    return {"success":False,"result":{"message":"Reservation not possible under given conditions (Fully occupied)"}}
    
    restaurant_book_db.append(book_info)
    with open("reservation/restaurant_book_db.json",'w') as f:
        json.dump(restaurant_book_db,f,indent=4)
    return {"success":True,"result":{"message":f"Booking Success. Booked information: {book_info}"}}

###train

def train_retrieve(train_schedule_id:int=None,day:str=None,departure:str=None,destination:str=None):    
    ## db load
    try:
        with open(f"db/train_db.json",'r') as f:
            db = json.load(f)
    except FileNotFoundError:
        return {"success":False,"result":{"message":"train retrieving is not available currently."}}
    
    ## none 인 거 다 걸러주고
    input_params = {"train_schedule_id":train_schedule_id,
                    "day":day,
                    "departure":departure,
                    "destination":destination}
    
    ## departure, destination 굳이 lower case 안해줌줌
    if input_params['departure']:
        input_params['departure'] = input_params['departure'].replace("\'","").replace("'","")
    if input_params['destination']:
        input_params['destination'] = input_params['destination'].replace("\'","").replace("'","")
    input_params = {param:input_params[param] for param in input_params if input_params[param]}
    if not input_params:
        return {"success":True,"result":db[:config["n_ret"]]} ## 모두 None이었으면 DB 전체 반환
    
    ## parameter type 점검
    input_params_type = {"train_schedule_id":int,"day":str,"departure":str,"destination":str}
    for param in input_params:
        if not isinstance(input_params[param],input_params_type[param]):
            return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}
    
    ## 사전 점검 끝났고, filtering
    final_entities = []
    for entity in db:
        cnt=0
        for param in input_params:
            if entity[param] == str(input_params[param]):
                cnt+=1
        if cnt==len(input_params):
            final_entities.append(entity)
    if config['n_ret']:
        if len(final_entities)>config["n_ret"]:
            final_entities = final_entities[:config["n_ret"]]
            
    return {"success":True,"result":final_entities}

def train_book(train_schedule_id:int=None,people:int=None):
    input_params = {"train_schedule_id":train_schedule_id,"people":people}
    ## 모두 required니까 다 들어왔는지 확인
    for param in input_params:
        if input_params[param] is None:
            return {"success":False,"result":{"message":f"Input parameter '{param}' is required parameter."}}
    
    ## input parameter의 type 확인
    input_params_type = {"train_schedule_id":int,"people":int}
    for param in input_params:
        if not isinstance(input_params[param],input_params_type[param]):
            return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}
        
    ## id가 db에 있는 것인지 확인
    try:
        with open(f"db/train_db.json",'r') as f:
            train_db = json.load(f)
    except FileNotFoundError:
        return {"success":False,"result":{"message":"Train booking is not available currently."}}
    train_id = {int(entity['train_schedule_id']):entity['train_schedule_id'] for entity in train_db}
    if input_params['train_schedule_id'] not in train_id:
        return {"success":False,"result":{"message":f"Train schedule id '{input_params['train_schedule_id']}' does not exsist. Please check the id properly."}}
    
    ## 모두 type 맞게 입력되었는지 확인
    book_info = {"train_schedule_id":train_schedule_id,"people":people}
    with open("reservation/train_book_db.json",'r') as f:
        train_book_db = json.load(f)
    if len(train_book_db)==0:
        reservation_id = 0
    else:
        reservation_id = train_book_db[-1]['reservation_id']+1
    book_info={"reservation_id":reservation_id,"reference_number":generate_random_string()}|book_info
    
    ## 여기서 no_book에 해당하는지 확인
    if "train_no_book_db.json" in os.listdir(f"db"):
        with open(f"db/train_no_book_db.json",'r') as f:
            train_no_book_db = json.load(f)
        
        for train_no_book in train_no_book_db:
            if train_no_book['train_schedule_id'] == book_info['train_schedule_id']:
                cnt=0
                for slot in ["people"]:
                    if str(book_info[slot]) == train_no_book[slot]:
                        cnt+=1
                if cnt == 1:
                    return {"success":False,"result":{"message":"Reservation not possible under given conditions (Fully occupied)"}}
    
    train_book_db.append(book_info)
    with open("reservation/train_book_db.json",'w') as f:
        json.dump(train_book_db,f,indent=4)
    return {"success":True,"result":{"message":f"Booking Success. Booked information: {book_info}"}}


### taxi
def generate_random_phone_number():
    number = '010' + ''.join(str(random.randint(0, 9)) for _ in range(8))
    return number

def taxi_book(leaveAt:str=None,arriveBy:str=None,destination:str=None,departure:str=None):
    ##required는 들어왔는지 확인
    input_params = {"leaveAt":leaveAt,"arriveBy":arriveBy,"destination":destination,"departure":departure}

    ## comma 제거
    if input_params['departure']:
        input_params['departure'] = input_params['departure'].replace("\'","").replace("'","")
    if input_params['destination']:
        input_params['destination'] = input_params['destination'].replace("\'","").replace("'","")
        
    for param in input_params:
        if param in ["destination","departure"] and input_params[param] is None:
            return {"success":False,"result":{"message":f"Input parameter '{param}' is required parameter."}}
    
    # leaveAt, arriveBy 둘 다 없을 경우
    if leaveAt==None and arriveBy == None:
        return {"success":False,"result":{"message":f"At least one either leaveAt or arriveBy should be inserted."}}

    ## 모두 type 맞게 입력되었는지 확인
    input_params_type = {"leaveAt":str,"arriveBy":str,"destination":str,"departure":str}
    for param in input_params:
        if input_params[param]:
            if not isinstance(input_params[param],input_params_type[param]):
                return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}
            if param == "leaveAt" or param == "arriveBy":
                if not check_time_format(input_params[param]):
                    return {"success":False,"result":{"message":f"Format of {param} is invalid. Check the API documentation properly."}}

    ## book info 생성    
    book_info = {"leaveAt":leaveAt,"arriveBy":arriveBy,"destination":destination,"departure":departure}
    try:
        with open("reservation/taxi_book_db.json",'r') as f:
            taxi_book_db = json.load(f)
    except FileNotFoundError:
        return {"success":False,"result":{"message":"Taxi booking is not available currently."}}
    if len(taxi_book_db)==0:
        reservation_id = 0
    else:
        reservation_id = taxi_book_db[-1]['reservation_id']+1
    book_info={"reservation_id":reservation_id,"reference_number":generate_random_string()}|book_info
    
    ## car type, phone number 생성기
    taxi_types = ["toyota","skoda","bmw","honda","ford","audi","lexus","volvo","volkswagen","tesla"]
    book_info['car_type'] = random.sample(taxi_types,1)[0]
    book_info['phone'] = generate_random_phone_number()
    taxi_book_db.append(book_info)
    with open("reservation/taxi_book_db.json",'w') as f:
        json.dump(taxi_book_db,f,indent=4)
    return {"success":True,"result":{"message":f"Booking Success. Booked information: {book_info}"}}


def book_cancel(domain:str=None,reservation_id:int=None):
    if reservation_id is None:
        return {"success":False,"result":{"message":f"reservation_id is required parameter."}}
    if domain is None:
        return {"success":False,"result":{"message":f"domain is required parameter."}}
    if not isinstance(reservation_id,int):
        return {"success":False,"result":{"message":f"reservation_id must be 'int' type"}}
    with open(f"reservation/{domain}_book_db.json",'r') as f:
        book_db = json.load(f)
    canceled=False
    for idx,reservation in enumerate(book_db):
        if reservation["reservation_id"] == reservation_id:
            del book_db[idx]
            canceled=True
            break
    if not canceled:
        return {"success":False,"result":{"message":f"Booking id '{reservation_id}' does not exsist."}}    
    with open(f"reservation/{domain}_book_db.json",'w') as f:
        json.dump(book_db,f,indent=4)
    with open("cancel.txt",'w') as f:
        json.dump(f"{domain}",f,indent=4)
    return {"success":True,"result":{"message":f"Booking id '{reservation_id}' has cancelled."}}

def show_app_description():
    app_description= [
        {
            "name":"train",
            "description":"An app capable of retrieving or booking train schedules."
        },
        {
            "name":"accommodation",
            "description":"An app capable of retrieving or booking accommodation."
        },
        {
            "name":"restaurant",
            "description":"An app capable of retrieving or restaurant."
        },
        {
            "name":"taxi",
            "description":"An app capable of retrieving or booking taxi."
        },
        {
            "name":"general",
            "description":"supporting APIs such as book canceling"
        }
    ]
    return {"success":True,"result":app_description}

def show_api_description(app_name:str=None):
    if app_name == None:
        return {"success":False,"result":{"message":"Input parameter 'app_name' is required parameter."}}
    with open("multiwoz_api_documentation.json",'r') as f:
        api_docs_list = json.load(f)
    current_app_api_list = deepcopy([
        {"name":api_docs['api_name'],"description":api_docs['description']} for api_docs in api_docs_list
        if api_docs['app_name'] == app_name
    ])
    del api_docs_list
    return {"success":True,"result":current_app_api_list}

def show_api_docs(app_name:str=None,api_name:str=None):
    input_params = {"app_name":app_name,"api_name":api_name}
    ## 모두 required니까 다 들어왔는지 확인
    for param in input_params:
        if input_params[param] is None:
            return {"success":False,"result":{"message":f"Input parameter '{param}' is required parameter."}}
    with open("multiwoz_api_documentation.json",'r') as f:
        api_docs_list = json.load(f)
    current_api_docs = [api_docs for api_docs in api_docs_list if api_docs['app_name'] == app_name and api_docs['api_name']==api_name]
    if len(current_api_docs)==0:
        return {"success":False,"result":{"message":"API does not exsist."}}
    return {"success":True,"result":current_api_docs[0]}

if __name__ == "__main__":
    payload = {"name":"rosa's bed and breakfast"}
    print(accommodation_retrieve(**payload))