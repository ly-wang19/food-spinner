from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class FavoriteRestaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amap_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    category = db.Column(db.String(100))
    rating = db.Column(db.Float)
    price = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'amap_id': self.amap_id,
            'name': self.name,
            'address': self.address,
            'category': self.category,
            'rating': self.rating,
            'price': self.price,
            'created_at': self.created_at.isoformat()
        }
