import json,os
import random
import string
## att는 book scenario는 없는 듯
def attraction_retrieve(area:str=None,name:str=None,type:str=None):
    # with open("tmp.json",'w')  as f:
    #     json.dump(os.listdir(),f,indent=4)

    ## db load
    with open("attraction_db.json",'r') as f:
        att_db = json.load(f)
    
    ## none 인 거 다 걸러주고
    input_params = {"area":area,"name":name,"type":type}
    
    if input_params['name']:
        input_params['name'] = input_params['name'].lower()
    
    input_params = {param:input_params[param] for param in input_params if input_params[param]}
    if not input_params:
        return {"success":True,"result":att_db} ## 나중에 에러 메세지의 자세한 정도로도 가능할 듯
    
    ## parameter type 점검
    input_params_type = {"area":str,"name":str,"type":str}
    for param in input_params:
        if not isinstance(input_params[param],input_params_type[param]):
            return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}
    
    final_entities = []
    for entity in att_db:
        cnt=0
        for param in input_params:
            if entity[param] == input_params[param]:
                cnt+=1
        if cnt==len(input_params):
            final_entities.append(entity)
            
    return {"success":True,"result":final_entities}

## Accomodation
def accomodation_retrieve(area:str=None, internet:bool=None, name:str=None, parking:bool=None, pricerange:str=None, stars:int=None, type:str=None):
    ## db load
    with open("db/hotel_db.json",'r') as f:
        hotel_db = json.load(f)
    
    ## none 인 거 다 걸러주고
    input_params = {"area":area, "internet":internet, "name":name, "parking":parking, "pricerange":pricerange, "stars":stars, "type":type}
    
    if input_params['name']:
        input_params['name'] = input_params['name'].lower()
    
    input_params = {param: value for param, value in input_params.items() if value is not None}
    
    ## 만약 input parameter 입력이 하나도 안되었으면
    if not input_params:
        return {"success":False,"result":hotel_db}
    
    ## parameter type 점검
    input_params_type = {"area":str, "internet":bool, "name":str, "parking":bool, "pricerange":str, "stars":int, "type":str}
    for param in input_params:
        if not isinstance(input_params[param],input_params_type[param]):
            return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}
        
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
            if entity[param] == input_params[param]:
                cnt+=1
        if cnt==len(input_params):
            final_entities.append(entity)
    return {"success":True,"result":final_entities}

## book의 경우, 좌석 및 방이 남았는지 까진 고려하지 않음
## 예약은 id를 받고 하는 형식임

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    

def accomodation_book(id:int=None,day:str=None,people:int=None,stay:int=None):
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
        with open(f"db/hotel_db.json",'r') as f:
            hotel_db = json.load(f)
    except FileNotFoundError:
        return {"success":False,"result":{"message":"Accomodation booking is not available currently."}}
    hotel_id = {int(entity['id']):entity['name'] for entity in  hotel_db}
    if input_params['id'] not in hotel_id:
        return {"success":False,"result":{"message":f"Accomodation id '{input_params['id']}' does not exsist. Please check the id properly."}}
    
    hotel_name = hotel_id[input_params['id']]
    
    ## 모두 type 맞게 입력되었는지 확인
    book_info = {"id":id,"name":hotel_name,"day":day,"people":people,"stay":stay}
    with open("reservation/hotel_book_db.json",'r') as f:
        hotel_book_db = json.load(f)
    if len(hotel_book_db)==0:
        reservation_id = 0
    else:
        reservation_id = hotel_book_db[-1]['reservation_id']+1
    book_info={"reservation_id":reservation_id,"reference_number":generate_random_string()}|book_info
    
    ## 여기서 no_book에 해당하는지 확인
    if "hotel_no_book_db.json" in os.listdir(f"db"):
        with open(f"db/hotel_no_book_db.json",'r') as f:
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
    
    ## 모든 시련을 통과함
    hotel_book_db.append(book_info)
    with open("reservation/hotel_book_db.json",'w') as f:
        json.dump(hotel_book_db,f,indent=4)
    return {"success":True,"result":{"message":f"Booking Success. Booked information: {book_info}"}}

def accomodation_book_cancel(reservation_id:int=None):
    if reservation_id is None:
        return {"success":False,"result":{"message":f"reservation_id is required parameter."}}
    if not isinstance(reservation_id,int):
        return {"success":False,"result":{"message":f"reservation_id must be 'int' type"}}
    with open("reservation/hotel_book_db.json",'r') as f:
        hotel_book_db = json.load(f)
    canceled=False
    for idx,reservation in enumerate(hotel_book_db):
        if reservation["reservation_id"] == reservation_id:
            del hotel_book_db[idx]
            canceled=True
            break
    if not canceled:
        return {"success":False,"result":{"message":f"Booking id '{reservation_id}' does not exsist."}}    
    with open("reservation/hotel_book_db.json",'w') as f:
        json.dump(hotel_book_db,f,indent=4)
    return {"success":True,"result":{"message":f"Booking id '{reservation_id}' has cancelled."}}

### Restaurant
def restaurant_retrieve(area:str=None,name:str=None,food:str=None,pricerange:str=None):
    ## db load
    with open(f"db/restaurant_db.json",'r') as f:
        att_db = json.load(f)
    
    ## none 인 거 다 걸러주고
    input_params = {"area":area,"name":name,"food":food,"pricerange":pricerange}
    if input_params['name']:
        input_params['name'] = input_params['name'].lower()
    input_params = {param:input_params[param] for param in input_params if input_params[param]}
    if not input_params:
        return {"success":True,"result":att_db} ## 모두 None이었으면 DB 전체 반환
    
    ## parameter type 점검
    input_params_type = {"area":str,"name":str,"food":str,"pricerange":str}
    for param in input_params:
        if not isinstance(input_params[param],input_params_type[param]):
            return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}
    
    final_entities = []
    for entity in att_db:
        cnt=0
        for param in input_params:
            if entity[param] == input_params[param]:
                cnt+=1
        if cnt==len(input_params):
            final_entities.append(entity)
            
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
    
    ## 모든 시련을 통과함
    restaurant_book_db.append(book_info)
    with open("reservation/restaurant_book_db.json",'w') as f:
        json.dump(restaurant_book_db,f,indent=4)
    return {"success":True,"result":{"message":f"Booking Success. Booked information: {book_info}"}}

###train

def train_retrieve(train_schedule_id:int=None,arriveBy:str=None,day:str=None,departure:str=None,destination:str=None,leaveAt:str=None):    
    ## db load
    with open(f"train_db.json",'r') as f:
        db = json.load(f)
    
    ## none 인 거 다 걸러주고
    input_params = {"train_schedule_id":train_schedule_id,
                    "arriveBy":arriveBy,
                    "day":day,
                    "departure":departure,
                    "destination":destination,
                    "leaveAt":leaveAt}
    if input_params['departure']: # 그 전에 lowercase
        input_params['departure'] = input_params['departure'].lower()
    if input_params['destination']:
        input_params['destination'] = input_params['destination'].lower()
    input_params = {param:input_params[param] for param in input_params if input_params[param]}
    if not input_params:
        return {"success":True,"result":db} ## 모두 None이었으면 DB 전체 반환
    
    ## parameter type 점검
    input_params_type = {"train_schedule_id":int,"arriveBy":str,"day":str,"departure":str,"destination":str,"leaveAt":str}
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
        
        #####작업필요######
        for train_no_book in train_no_book_db:
            if train_no_book['train_schedule_id'] == book_info['train_schedule_id']: ## 될려나 모르겠다
                cnt=0
                for slot in ["people"]: ## train 예약에서 제약은 사람 수만?
                    if str(book_info[slot]) == train_no_book[slot]:
                        cnt+=1
                if cnt == 1: ## 현재 예약하려는 조건이 no_book의 조건 중 하나랑 완전히 일치할 경우
                    ## 단, 뭐땜에 예약 안됬는지를 안알려줌
                    return {"success":False,"result":{"message":"Reservation not possible under given conditions (Fully occupied)"}}
        #####작업필요######
    
    ## 모든 시련을 통과함
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
    for param in input_params:
        if param in ["destination","departure"] and input_params[param] is None:
            return {"success":False,"result":{"message":f"Input parameter '{param}' is required parameter."}}
    ## 모두 type 맞게 입력되었는지 확인
    input_params_type = {"leaveAt":str,"arriveBy":str,"destination":str,"departure":str}
    for param in input_params:
        if input_params[param]:
            if not isinstance(input_params[param],input_params_type[param]):
                return {"success":False,"result":{"message":f"Type of {param} must be {input_params_type[param]}"}}
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