import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import math

class WeatherAnalytics:
    def __init__(self):
        self.model = LinearRegression()
    
    def generate_historical_data(self, current_temp, days_back=30):
        dates = []
        temps = []
        humidity = []
        rain = []
        
        base_date = datetime.now()
        
        for i in range(days_back, 0, -1):
            date = base_date - timedelta(days=i)
            dates.append(date)
            
            day_of_year = date.timetuple().tm_yday
            seasonal_factor = math.sin(2 * math.pi * day_of_year / 365) * 5
            
            temp = current_temp + seasonal_factor + np.random.normal(0, 2)
            temps.append(round(temp, 1))
            
            hum = 60 + (25 - abs(temp - 25)) * 0.5 + np.random.normal(0, 5)
            humidity.append(min(100, max(20, round(hum, 1))))
            
            rain_prob = max(0, min(100, 30 + seasonal_factor * 2 + np.random.normal(0, 10)))
            rain.append(round(rain_prob, 1))
        
        return {
            'dates': [d.strftime('%Y-%m-%d') for d in dates],
            'temperatures': temps,
            'humidity': humidity,
            'rain_probability': rain
        }
    
    def predict_temperature_trend(self, historical_temps, future_days=7):
        if len(historical_temps) < 5:
            return None
            
        X = np.array(range(len(historical_temps))).reshape(-1, 1)
        y = np.array(historical_temps)
        
        self.model.fit(X, y)
        
        future_X = np.array(range(len(historical_temps), 
                                len(historical_temps) + future_days)).reshape(-1, 1)
        predictions = self.model.predict(future_X)
        
        slope = self.model.coef_[0]
        trend = "increasing" if slope > 0.1 else "decreasing" if slope < -0.1 else "stable"
        
        predictions_rounded = [round(p, 1) for p in predictions]
        confidence = min(95, max(60, 100 - abs(slope) * 10))
        
        return {
            'predictions': predictions_rounded,
            'trend': trend,
            'slope': round(slope, 3),
            'confidence': round(confidence, 1),
            'next_7_days': predictions_rounded[:7]
        }
    
    def predict_rainfall(self, historical_rain, future_days=7):
        if len(historical_rain) < 5:
            return None
            
        weights = np.array([0.5**i for i in range(len(historical_rain))][::-1])
        weights = weights / weights.sum()
        
        base_pred = np.average(historical_rain[-5:])
        
        predictions = []
        for i in range(future_days):
            day_variation = np.sin(i * 0.9) * 3
            pred = base_pred + day_variation + np.random.normal(0, 2)
            predictions.append(max(0, min(100, round(pred, 1))))
        
        recent_avg = np.mean(historical_rain[-7:])
        older_avg = np.mean(historical_rain[:-7]) if len(historical_rain) > 7 else recent_avg
        rain_trend = "increasing" if recent_avg > older_avg + 2 else "decreasing" if recent_avg < older_avg - 2 else "stable"
        
        return {
            'predictions': predictions,
            'trend': rain_trend,
            'next_7_days': predictions[:7],
            'high_risk_days': [i for i, p in enumerate(predictions) if p > 70]
        }