from bs4 import BeautifulSoup
import requests
import re
from datetime import date, datetime
import time
import json
from geopy.geocoders import Nominatim
from googletrans import Translator
from selenium import webdriver
from selenium.webdriver.common.by import By
import argparse


def translate(text: str):
    """ chịu trách nhiệm cho chyển đổi từ tiếng nhật sang tiếng anh và trung"""
    try:
        translator = Translator()
        target_langs = {
            "en": "en",
            "zh_CN": "zh-CN",
            "zh_TW": "zh-TW"
        }
        results = {}
        for key, lang in target_langs.items():
            translated = translator.translate(text, src="ja", dest=lang)
            results[key] = translated.text

        return results

    except Exception as e:
        print(f"Lỗi khi dịch: {e}")
        return {"en": None, "zh_CN": None, "zh_TW": None}

def get_location(address:str):
    """ Chịu trách nhiệm lấy thông tin vị trí tọa độ của địa chỉ long  và lat """
    geolocator = Nominatim(user_agent="jp_property_locator")
    location = geolocator.geocode(address, language='en')
    if location:
        return {"lat":location.latitude,"long":location.longitude}
    else:
        print("Không tìm thấy tọa độ.")
        return {"lat":None,"long":None}
    
def clean_text(text:str):
    """ clean các kí tự thừa trong chuỗi cần xử lý"""
    return ' '.join(text.split())

def basicInfoH1(building_info):
     """ xử lý các giá trị của thẻ h1 chứa các giá trị về tên tòa nhà, tầng, số phòng của văn phòng cho thuê """
     cleandata = clean_text(building_info)
    
     match = re.match(r"(.+?)\s+(\d+)階(\d+)", cleandata)
     if match:
        building_name = match.group(1)
        floor_no = match.group(2)
        unit_no = match.group(3)
        
        translate_name = translate(building_name)
        
        return {
            'building_name_ja': building_name,
            'building_name_en': translate_name["en"],
            'building_name_zh_CN':translate_name["zh_CN"],
            'building_name_zh_TW': translate_name["zh_TW"],
            'floor_no': floor_no,
            'unit_no' : unit_no 
        }
     else:
        print("Không tìm thấy thông tin phù hợp.")
        return {}

def buildroomSummaryOverview(dl):
    """ xử lý các thông tin trong class building_sumary_overview"""
    # Dictionary lưu kết quả
    result = {}
    # Dictionary thông tin để xử lý
    building_info = {}
    for div in dl.find_all('div'):
        dt = div.find('dt')
        dd = div.find_all('dd')
        if dt and dd:
            key = dt.text.strip()
            value = dd[-1].text.strip()
        building_info[key] = value
    # lấy thông tin địa chỉ
    address =building_info['所在地']
    
    prefecture_match = re.match(r'^(東京都|北海道|(?:京都|大阪)府|..県)', address)
    prefecture = prefecture_match.group(0) if prefecture_match else None

    remain = address[len(prefecture):] if prefecture else address

    city_match = re.match(r'^[^0-9一二三四五六七八九十百千]+?[区市郡町村]', remain)
    city = city_match.group(0) if city_match else None

    remain2 = remain[len(city):] if city else remain

    district_match = re.match(r'^[^0-9一二三四五六七八九十百千]+', remain2)
    district = district_match.group(0) if district_match else None

    chome_banchi = remain2[len(district):] if district else remain2
    
    date_str = building_info['竣工日']

    formats = [
            "%Y年%m月%d日",
            "%Y年%m月",     
            "%Y年",         
        ]
    for fmt in formats:
        try:
            date_obj=datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    result['prefecture']=prefecture
    result['city']=city
    result['district']=district
    result['chome_banchi']=chome_banchi
    result['year']=date_obj.year
    
    address_en = translate(address)
    location = get_location(address_en['en'])
    
    result['map_lat'] = location['lat']
    result['map_lng'] = location['long']

    # lấy thông tin về chi phí
    rent_info = building_info['賃料・管理費・共益費']
    if rent_info:
        parts = [p.strip() for p in rent_info.split('/')]

        if len(parts) >= 1:
            rent_match = re.search(r'([\d,]+)', parts[0])
            if rent_match:
                monthly_rent = int(rent_match.group(1).replace(',', ''))

        if len(parts) >= 2:
            maintenance_match = re.search(r'([\d,]+)', parts[1])
            if maintenance_match:
                monthly_maintenance = int(maintenance_match.group(1).replace(',', ''))

    # Lấy deposit
    deposit_info = building_info['敷金／礼金']
    if deposit_info:
        parts = [p.strip() for p in deposit_info.split('/')]
        if len(parts) >= 1:
            if "無" not in parts[0]:
                month_match = re.search(r'([\d\.]+)ヶ月', parts[0])
                if month_match:
                    months_deposit = float(month_match.group(1))
                    if monthly_rent is not None:
                        numeric_deposit = int(months_deposit*monthly_rent)
        if len(parts) >= 2:
            if "無" not in parts[1]:
                key_match = re.search(r'([\d\.]+)ヶ月', parts[1])
                if key_match:
                    months_key = float(key_match.group(1))
                    if monthly_rent is not None:
                        numeric_key = int(months_key * monthly_rent)
            else:
                months_key = None
                numeric_key = None

    result['monthly_rent']=monthly_rent
    result['monthly_maintenance'] = monthly_maintenance
    result['months_deposit']=months_deposit
    result['numeric_deposit'] = numeric_deposit
    result['months_key']=months_key
    result['numeric_key']=numeric_key

    # lấy dữ liệu roomtype và size
    room_info = building_info['間取り・面積']
    if room_info:
        parts = [p.strip() for p in room_info.split('/')]
        room_type=parts[0]
        size = parts[1]
    else:
        room_type = None
        size = None
    result['room_type'] = room_type
    result['size'] = size

    return result

def updateData(property_data: dict, data: dict):
    for key in data:
        if key in property_data:
            property_data[key] = data[key]
            print(f"Updated: {key}")
        else:
            print(f"Key không khớp: {key}")
def getImgandCatagory(url:str,soup:BeautifulSoup):
    """ Lấy các url của ảnh và phân loại theo catagory """
    # dùng selenium 
    result ={}
    driver = webdriver.Chrome()
    driver.get(url)
    index_local = 1
    images_data = soup.find('div', class_='swiper-wrapper')
    if images_data:
        images = images_data.find_all('img')
        for index, img in enumerate(images, start=1):
            result[f'image_url_{index}']=img['src']
            result[f'image_category_{index}']= 'floorplan'
            index_local +=1
    else:
        print("Không tìm thấy swiper-wrapper sau khi click")
    try:
        button_exterior = driver.find_element(By.CSS_SELECTOR, 'button[data-js-buildroom-slide-tab="exterior"]')
    except:

        button_exterior = None

    if button_exterior:
        driver.execute_script("arguments[0].scrollIntoView(true);", button_exterior)
        time.sleep(1)
        button_exterior.click() 
        time.sleep(2) 

        soup = BeautifulSoup(driver.page_source, "html.parser")
        div = soup.find('div', class_='swiper-wrapper')
        if div:
            images = div.find_all('img')
            for index, img in enumerate(images, start=index_local):

                result[f'image_url_{index}']=img['src']
                result[f'image_category_{index}']= 'exterior'
                
        else:
            print("Không tìm thấy swiper-wrapper sau khi click")
    else:
        print("Not found button")
    driver.quit()
    return result

def buildroomDetail(div, monthly_rent):
    """Lấy các thông tin từ thẻ div class buildroom Detail """
    result = {}
    dl_list = div.find_all('dl', class_='c-buildroom-detail__list') if div else []
    building_detail ={}

    for dl in dl_list:
        dt = dl.find('dt')
        dd = dl.find('dd')
        if dt and dd:
            key = dt.text.strip()
            value = ''.join(dd.find_all(string=True, recursive=True)).strip()
            if key == "giao thông": 
                data_div = dd.find('div', class_='__data')
                value = ''.join(data_div.find_all().strip() if data_div else value)
            building_detail[key] = value

    transport = building_detail['交通']

    lines = [line.strip() for line in transport.split('\n') if line.strip()]
    blocks = []

    for i in range(0, len(lines), 4):
        block = lines[i:i+4]
        if len(block) == 4:
            blocks.append(block)

    for idx, block in enumerate(blocks[:5]):
        line_type, line_name, station_name, walk_info = block
        walk_match = re.search(r'徒歩(\d+)分', walk_info)
        walk_time = int(walk_match.group(1)) if walk_match else None

        result[f"station_name_{idx+1}"] = station_name
        result[f"train_line_name_{idx+1}"] = line_name
        result[f"walk_{idx+1}"] = walk_time

    available_from = building_detail['入居可能日']
    result['available_from']= available_from

    facing = building_detail['方位']

    facing_directions = [
        "facing_north", "facing_northeast", "facing_east", "facing_southeast",
        "facing_south", "facing_southwest", "facing_west", "facing_northwest"
    ]

    for direction in facing_directions:
        result[direction] = 'N'

    facing_map = {
        '北': 'facing_north',
        '北東': 'facing_northeast', 
        '東': 'facing_east',
        '南東': 'facing_southeast',
        '南': 'facing_south',
        '南西': 'facing_southwest',  
        '西': 'facing_west',
        '北西': 'facing_northwest'
    }
    if facing in facing_map:
        result[facing_map[facing]] = 'Y'


    structure_floors = building_detail['規模構造']
    if structure_floors:
        structure_match = re.match(r'(.+?造)', structure_floors)
        structure = structure_match.group(1) if structure_match else None

        # Floors above ground
        floors_match = re.search(r'地上(\d+)階', structure_floors)
        floors = int(floors_match.group(1)) if floors_match else None

        # Basement floors
        basement_match = re.search(r'地下(\d+)階', structure_floors)
        basement_floors = int(basement_match.group(1)) if basement_match else None
    else:
        structure = None
        floors = None
        basement_floors = None
    
    result['structure'] = structure
    result['floor_no'] = floors
    result['basement_floors'] = basement_floors


    building_description=building_detail['備考']
    building_description_multiple_languae = translate(building_description)
    result['building_description_ja'] = building_description
    result['building_description_en'] = building_description_multiple_languae['en']
    result['building_description_zh_CN'] = building_description_multiple_languae['zh_CN']
    result['building_description_zh_TW'] = building_description_multiple_languae['zh_TW']
    
    parking = building_detail['駐車場']

    if parking:
        text = parking.strip()
        no_keywords = ["無", "なし", "無し", "含まれていません", "空無"]
        if any(kw in text for kw in no_keywords):
            have_parking = "N"
        yes_keywords = ["有", "あり", "有り", "込", "利用可", "空有", "付き", "近隣", "別途契約"]
        if any(kw in text for kw in yes_keywords):
            have_parking = "Y"
        if re.search(r'\d+[,，]?\d*円', text):
            have_parking = "Y"
    else:
        have_parking = 'N'
    
    result['parking']=have_parking

    renewal_fee= building_detail['更新料']

    if renewal_fee:
        match = re.search(r'(\d+)\s*ヶ月', renewal_fee.strip())
        if match:
            month_renewal = int(match.group(1))
           
        else:
            month_renewal = 0
    else:
        month_renewal = 0
    
    result['months_renewal'] = month_renewal
    numeric_renewal = month_renewal *monthly_rent
    result['numeric_renewal'] = numeric_renewal

    # xử các checkbox
    utilities =building_detail['専有部・共用部設備']

    if not utilities:
        utilities = ""

    mapping = {
        "aircon": ["エアコン"],
        "aircon_heater": ["冷暖房"],
        "all_electric": ["オール電化"],
        "auto_fill_bath": ["オートバス", "自動湯張り"],
        "balcony": ["バルコニー", "ベランダ"],
        "bath": ["バス", "浴室"],
        "bath_water_heater": ["追い焚き", "給湯追い焚き"],
        "blinds": ["ブラインド"],
        "bs": ["BS", "衛星放送"],
        "cable": ["CATV", "ケーブルテレビ"],
        "carpet": ["カーペット"],
        "cleaning_service": ["清掃サービス", "クリーニングサービス"],
        "counter_kitchen": ["カウンターキッチン", "対面Ｋ"],
        "dishwasher": ["食器洗浄機", "食洗機"],
        "drapes": ["カーテン", "ドレープ"],
        "female_only": ["女性限定", "女性専用"],
        "fireplace": ["暖炉"],
        "flooring": ["フローリング"],
        "full_kitchen": ["フルキッチン"],
        "furnished": ["家具付き", "家具家電付き"],
        "gas": ["ガス", "都市ガス", "プロパンガス"],
        "induction_cooker": ["IHクッキングヒーター", "IHコンロ"],
        "internet_broadband": ["インターネット", "ブロードバンド"],
        "internet_wifi": ["WiFi", "無線LAN"],
        "japanese_toilet": ["和式トイレ"],
        "linen": ["リネン"],
        "loft": ["ロフト"],
        "microwave": ["電子レンジ"],
        "oven": ["オーブン"],
        "phoneline": ["電話回線"],
        "range": ["コンロ", "ガスコンロ", "IHコンロ"],
        "refrigerator": ["冷蔵庫"],
        "refrigerator_freezer": ["冷凍冷蔵庫", "冷凍庫付き"],
        "roof_balcony": ["ルーフバルコニー", "屋上バルコニー"],
        "separate_toilet": ["トイレ別", "バストイレ別"],
        "shower": ["シャワー"],
        "soho": ["SOHO可", "事務所利用可"],
        "storage": ["収納", "クロゼット", "押入", "物置"],
        "student_friendly": ["学生可", "学生歓迎"],
        "system_kitchen": ["システムＫ", "システムキッチン"],
        "tatami": ["畳", "和室"],
        "underfloor_heating": ["床暖房"],
        "unit_bath": ["ユニットバス"],
        "utensils_cutlery": ["調理器具", "食器付き"],
        "veranda": ["ベランダ"],
        "washer_dryer": ["乾燥機付き洗濯機", "洗濯乾燥機"],
        "washing_machine": ["洗濯機", "室内洗濯機置場"],
        "washlet": ["ウォシュレット", "洗浄便座"],
        "western_toilet": ["洋式トイレ"],
        "yard": ["庭"],
        "bicycle_parking": ["駐輪場"],
        "motorcycle_parking": ["バイク置場", "駐輪場（バイク）"],
        "autolock": ["オートロック"],
        "credit_card": ["クレジットカード"],
        "concierge": ["コンシェルジュ", "フロントサービス"],
        "delivery_box": ["宅配ロッカー", "宅配ボックス"],
        "elevator": ["エレベータ"],
        "gym": ["ジム", "フィットネス"],
        "newly_built": ["新築"],
        "pets": ["ペット可", "ペット相談", "ペット飼育可"],
        "swimming_pool": ["プール"]
    }

    for field in mapping:
        result[f'{field}'] = 'N'

    for field, keywords in mapping.items():
        if any(kw in utilities for kw in keywords):
            result[f'{field}'] = "Y"

    return result

def createCSVIdandDate(url):
    result ={}
    url_match = re.search(r'/tatemono/(\d+)/(\d+)', url)
    if url_match:
        building_id, unit_id = url_match.groups()
        result['property_csv_id'] = f"{building_id}-{unit_id}"
    #timestamp = int(time.time())
    iso_time = datetime.now().isoformat()
 
    result['create_date'] = str(iso_time)

    return result

def main():
    """ Nơi xử lý chính"""
    parser = argparse.ArgumentParser(description="Lấy thông tin từ URL")
    parser.add_argument('--url', type=str, required=True, help='Đường dẫn URL cần xử lý')
    args = parser.parse_args()

    # Lấy nội dung từ URL
    response = requests.get(args.url)
    url = args.url
    #soup = BeautifulSoup(response.content, 'html.parser')
    #url ="https://www.mitsui-chintai.co.jp/rf/tatemono/10815/201"
    #response = requests.get(url )
    soup = BeautifulSoup(response.content, 'html.parser')
    if response.status_code == 200:
        print("Tải trang thành công")
    else:
        print(f"Lỗi tải trang: {response.status_code}")
    property_data = {
        
        "link": url, 
        "property_csv_id": None, 
        "postcode": None,
        "prefecture": None,
        "city": None,
        "district": None,
        "chome_banchi": None,
        "building_type": None,
        "year": None,
        "building_name_en": None,
        "building_name_ja": None,
        "building_name_zh_CN": None,
        "building_name_zh_TW": None,
        "building_description_en": None,
        "building_description_ja": None,
        "building_description_zh_CN": None,
        "building_description_zh_TW": None,
        "building_landmarks_en": None,
        "building_landmarks_ja": None,
        "building_landmarks_zh_CN": None,
        "building_landmarks_zh_TW": None,
        "station_name_1": None,
        "train_line_name_1": None,
        "walk_1": None,
        "bus_1": None,
        "car_1": None,
        "cycle_1": None,
        "station_name_2": None,
        "train_line_name_2": None,
        "walk_2": None,
        "bus_2": None,
        "car_2": None,
        "cycle_2": None,
        "station_name_3": None,
        "train_line_name_3": None,
        "walk_3": None,
        "bus_3": None,
        "car_3": None,
        "cycle_3": None,
        "station_name_4": None,
        "train_line_name_4": None,
        "walk_4": None,
        "bus_4": None,
        "car_4": None,
        "cycle_4": None,
        "station_name_5": None,
        "train_line_name_5": None,
        "walk_5": None,
        "bus_5": None,
        "car_5": None,
        "cycle_5": None,
        "map_lat": None,
        "map_lng": None,
        "num_units": None,
        "floors": None, 
        "basement_floors": None,
        "parking": None,
        "parking_cost": None,
        "bicycle_parking": None,
        "motorcycle_parking": None,
        "structure": None,
        "building_notes": None,
        "building_style": None,
        "autolock": None,
        "credit_card": None,
        "concierge": None,
        "delivery_box": None,
        "elevator": None,
        "gym": None,
        "newly_built": None,
        "pets": None,
        "swimming_pool": None,
        "ur": None,
        "room_type": None,
        "size": None,
        "unit_no": None,
        "ad_type": None,
        "available_from": None,
        "property_description_en": None,
        "property_description_ja": None,
        "property_description_zh_CN": None,
        "property_description_zh_TW": None,
        "property_other_expenses_en": None,
        "property_other_expenses_ja": None,
        "property_other_expenses_zh_CN": None,
        "property_other_expenses_zh_TW": None,
        "featured_a": None,
        "featured_b": None,
        "featured_c": None,
        "floor_no": None,
        "monthly_rent": None,
        "monthly_maintenance": None,
        "months_deposit": None,
        "numeric_deposit": None,
        "months_key": None,
        "numeric_key": None,
        "months_guarantor": None,
        "numeric_guarantor": None,
        "months_agency": None,
        "numeric_agency": None,
        "months_renewal": None,
        "numeric_renewal": None,
        "months_deposit_amortization": None,
        "numeric_deposit_amortization": None,
        "months_security_deposit": None,
        "numeric_security_deposit": None,
        "lock_exchange": None,
        "fire_insurance": None,
        "other_initial_fees": None,
        "other_subscription_fees": None,
        "no_guarantor": None,
        "guarantor_agency": None,
        "guarantor_agency_name": None,
        "rent_negotiable": None,
        "renewal_new_rent": None,
        "lease_date": None,
        "lease_months": None,
        "lease_type": None,
        "short_term_ok": None,
        "balcony_size": None,
        "property_notes": None,
        "facing_north": None,
        "facing_northeast": None,
        "facing_east": None,
        "facing_southeast": None,
        "facing_south": None,
        "facing_southwest": None,
        "facing_west": None,
        "facing_northwest": None,
        "aircon": None,
        "aircon_heater": None,
        "all_electric": None,
        "auto_fill_bath": None,
        "balcony": None,
        "bath": None,
        "bath_water_heater": None,
        "blinds": None,
        "bs": None,
        "cable": None,
        "carpet": None,
        "cleaning_service": None,
        "counter_kitchen": None,
        "dishwasher": None,
        "drapes": None,
        "female_only": None,
        "fireplace": None,
        "flooring": None,
        "full_kitchen": None,
        "furnished": None,
        "gas": None,
        "induction_cooker": None,
        "internet_broadband": None,
        "internet_wifi": None,
        "japanese_toilet": None,
        "linen": None,
        "loft": None,
        "microwave": None,
        "oven": None,
        "phoneline": None,
        "range": None,
        "refrigerator": None,
        "refrigerator_freezer": None,
        "roof_balcony": None,
        "separate_toilet": None,
        "shower": None,
        "soho": None,
        "storage": None,
        "student_friendly": None,
        "system_kitchen": None,
        "tatami": None,
        "underfloor_heating": None,
        "unit_bath": None,
        "utensils_cutlery": None,
        "veranda": None,
        "washer_dryer": None,
        "washing_machine": None,
        "washlet": None,
        "western_toilet": None,
        "yard": None,
        "youtube": None,
        "vr_link": None,
        "image_category_1": None,
        "image_url_1": None,
        "image_category_2": None,
        "image_url_2": None,
        "image_category_3": None,
        "image_url_3": None,
        "image_category_4": None,
        "image_url_4": None,
        "image_category_5": None,
        "image_url_5": None,
        "image_category_6": None,
        "image_url_6": None,
        "image_category_7": None,
        "image_url_7": None,
        "image_category_8": None,
        "image_url_8": None,
        "image_category_9": None,
        "image_url_9": None,
        "image_category_10": None,
        "image_url_10": None,
        "image_category_11": None,
        "image_url_11": None,
        "image_category_12": None,
        "image_url_12": None,
        "image_category_13": None,
        "image_url_13": None,
        "image_category_14": None,
        "image_url_14": None,
        "image_category_15": None,
        "image_url_15": None,
        "image_category_16": None,
        "image_url_16": None,
        "numeric_guarantor_max": None,
        "discount": None,
        "create_date": None,
    }

    # lấy thông tin từ lớp "c-buildroom__summary-h"
    basic_info = soup.find('h1',class_="c-buildroom__summary-h")
    data_building = basic_info.text.strip()
    building_info = basicInfoH1(data_building)
    updateData(property_data, building_info)

    # lấy thông tin từ lớp 'c-buildroom__summary-overview-list'
    dl = soup.find('dl', class_='c-buildroom__summary-overview-list')
    building_summary = buildroomSummaryOverview(dl)
    updateData(property_data,building_summary)

    #lấy các thông tin từ lớp building detail
    div = soup.find('div', class_='c-buildroom-sect__body')
    buiding_detail = buildroomDetail(div,property_data['monthly_rent'])
    updateData(property_data, buiding_detail)
    
    # láy thông tin về các ảnh và catagory
    img_catagory = getImgandCatagory(url,soup)
    updateData(property_data,img_catagory)
    id_and_date= createCSVIdandDate(url)
    updateData(property_data,id_and_date)

    for key,value in property_data.items():
        print(f'{key} : {value}')
    
    # Lưu vào file json
    with open("DataCrawl.json", "w", encoding="utf-8") as file:
        json.dump(property_data, file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()