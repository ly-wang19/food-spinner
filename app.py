from flask import Flask, render_template, jsonify, request
import requests
import random
import os
import logging
from dotenv import load_dotenv
from models import db, FavoriteRestaurant

app = Flask(__name__)
load_dotenv()

# 配置日志级别为 DEBUG
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurants.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 从环境变量获取API密钥，如果没有则使用默认值
AMAP_KEY = os.getenv('AMAP_KEY', '6128b7e34be4fce79dc0dd2d4167f9bf')

db.init_app(app)

# 创建数据库表
with app.app_context():
    db.create_all()

def get_nearby_restaurants(location, radius=3000, types='050000', page=1):
    """
    使用高德地图 API 获取附近餐厅
    types='050000' 表示餐饮服务类POI
    """
    url = 'https://restapi.amap.com/v3/place/around'
    
    # 确保位置格式正确（经度在前，纬度在后）
    try:
        lon, lat = map(float, location.split(','))
        location = f"{lon},{lat}"
    except Exception as e:
        app.logger.error(f"Invalid location format: {location}, error: {e}")
        return []

    params = {
        'key': AMAP_KEY,
        'location': location,
        'radius': radius,
        'types': types,
        'page': page,
        'offset': 25,
        'extensions': 'all'
    }
    
    app.logger.info(f"Calling Amap API with params: {params}")
    
    try:
        response = requests.get(url, params=params)
        app.logger.debug(f"Amap API raw response: {response.text}")
        
        data = response.json()
        if data.get('status') == '1':
            restaurants = data.get('pois', [])
            app.logger.info(f"Successfully found {len(restaurants)} restaurants")
            return restaurants
            
        app.logger.error(f"Amap API error: {data}")
        error_info = data.get('info', 'Unknown error')
        error_code = data.get('infocode', 'No code')
        app.logger.error(f"Error details - Code: {error_code}, Info: {error_info}")
        return []
    except Exception as e:
        app.logger.error(f"Error fetching restaurants: {str(e)}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/restaurants')
def get_restaurants():
    location = request.args.get('location', '116.473168,39.993015')
    price = request.args.get('price')
    rating = request.args.get('rating')
    radius = request.args.get('radius', 3000)
    
    app.logger.info(f"Fetching restaurants with params: location={location}, price={price}, rating={rating}, radius={radius}")
    
    restaurants = get_nearby_restaurants(location, radius=radius)
    
    # 根据价格和评分筛选
    filtered_restaurants = []
    for r in restaurants:
        meets_criteria = True
        
        if price and not r.get('cost', '').startswith(price):
            meets_criteria = False
            app.logger.debug(f"Restaurant {r.get('name')} filtered out due to price")
        
        if rating:
            try:
                rest_rating = float(r.get('biz_ext', {}).get('rating', 0))
                if rest_rating < float(rating):
                    meets_criteria = False
                    app.logger.debug(f"Restaurant {r.get('name')} filtered out due to rating")
            except (ValueError, TypeError) as e:
                app.logger.warning(f"Invalid rating for restaurant {r.get('name')}: {e}")
                meets_criteria = False
        
        if meets_criteria:
            filtered_restaurants.append(r)
    
    app.logger.info(f"Found {len(filtered_restaurants)} restaurants after filtering")
    return jsonify(filtered_restaurants)

@app.route('/api/recommend')
def recommend():
    location = request.args.get('location', '116.473168,39.993015')
    price = request.args.get('price')
    rating = request.args.get('rating')
    radius = request.args.get('radius', 3000)
    
    app.logger.info(f"Getting recommendation with params: location={location}, price={price}, rating={rating}, radius={radius}")
    
    restaurants = get_nearby_restaurants(location, radius=int(radius))
    app.logger.info(f"Found {len(restaurants)} restaurants before filtering")
    
    # 根据价格和评分筛选
    filtered_restaurants = []
    for r in restaurants:
        meets_criteria = True
        
        if price and not r.get('cost', '').startswith(price):
            meets_criteria = False
            app.logger.debug(f"Restaurant {r.get('name')} filtered out due to price")
        
        if rating:
            try:
                rest_rating = float(r.get('biz_ext', {}).get('rating', 0))
                if rest_rating < float(rating):
                    meets_criteria = False
                    app.logger.debug(f"Restaurant {r.get('name')} filtered out due to rating")
            except (ValueError, TypeError) as e:
                app.logger.warning(f"Invalid rating for restaurant {r.get('name')}: {e}")
                meets_criteria = False
        
        if meets_criteria:
            filtered_restaurants.append(r)
    
    app.logger.info(f"Found {len(filtered_restaurants)} restaurants after filtering")
    
    if filtered_restaurants:
        chosen = random.choice(filtered_restaurants)
        app.logger.info(f"Recommending restaurant: {chosen.get('name')}")
        return jsonify(chosen)
    
    app.logger.warning("No restaurants found matching criteria")
    return jsonify({'error': 'No restaurants found'})

@app.route('/api/favorites', methods=['GET', 'POST', 'DELETE'])
def handle_favorites():
    if request.method == 'GET':
        favorites = FavoriteRestaurant.query.all()
        return jsonify([f.to_dict() for f in favorites])
    
    elif request.method == 'POST':
        data = request.json
        favorite = FavoriteRestaurant(
            amap_id=data['id'],
            name=data['name'],
            address=data['address'],
            category=data['type'],
            rating=float(data['biz_ext']['rating']) if data.get('biz_ext', {}).get('rating') else None,
            price=data.get('cost', '')
        )
        db.session.add(favorite)
        db.session.commit()
        return jsonify(favorite.to_dict())
    
    elif request.method == 'DELETE':
        restaurant_id = request.args.get('id')
        favorite = FavoriteRestaurant.query.filter_by(amap_id=restaurant_id).first()
        if favorite:
            db.session.delete(favorite)
            db.session.commit()
            return jsonify({'message': 'Restaurant removed from favorites'})
        return jsonify({'error': 'Restaurant not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5002)
