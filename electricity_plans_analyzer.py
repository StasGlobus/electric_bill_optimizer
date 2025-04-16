import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

class TimeSlot:
    """Represents a time slot with specific discount rates."""
    def __init__(self, start_hour: int, end_hour: int, days: List[str], discount: float):
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.days = days
        self.discount = discount

class ElectricityPlan:
    """Represents an electricity plan with its features and time slots."""
    def __init__(self, raw_data: Dict[str, Any]):
        self.company = raw_data.get('company', '')
        self.name = raw_data.get('name', '')
        self.description = raw_data.get('description', '')
        self.raw_discount = raw_data.get('discount', '')
        self.features = raw_data.get('features', [])
        self.additional_details = raw_data.get('additional_details', [])
        self.contact_button_text = raw_data.get('contact_button_text', '')
        
        self.base_discount = self._extract_base_discount()
        self.time_slots = self._extract_time_slots()
        self.requires_smart_meter = any('מונה חכם' in detail for detail in self.additional_details)
        self.has_fixed_price = any('מחיר קבוע' in feature for feature in self.features)
        self.has_online_management = any('ניהול מקוון' in feature for feature in self.features)

    def _extract_base_discount(self) -> float:
        """Extract the base discount from the plan data."""
        discount = self._extract_discount(self.raw_discount)
        if discount == 0:
            for feature in self.features:
                if 'הנחה' in feature:
                    discount = self._extract_discount(feature)
                    if discount > 0:
                        return discount
        return discount

    def _extract_discount(self, text: str) -> float:
        """Extract discount percentage from text using multiple patterns."""
        if not text:
            return 0.0
        
        patterns = [
            r'(\d+)\s*%',
            r'(\d+)\s*אחוז',
            r'הנחה\s*(\d+)',
            r'(\d+)\s*הנחה'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return 0.0

    def _extract_time_slots(self) -> List[TimeSlot]:
        """Extract time slots and their discounts from features."""
        time_slots = []
        for feature in self.features:
            time_match = re.search(r'(\d{1,2}):(\d{2})\s*(?:עד|עד ל-)\s*(\d{1,2}):(\d{2})', feature)
            if time_match:
                start_hour = int(time_match.group(1))
                end_hour = int(time_match.group(3))
                
                days_match = re.search(r'ימים\s*([א-ת\'-]+)', feature)
                days = self._parse_days(days_match.group(1) if days_match else 'א-ה')
                
                discount = self._extract_discount(feature)
                if discount == 0:
                    discount = self.base_discount
                
                time_slots.append(TimeSlot(start_hour, end_hour, days, discount))
        
        if not time_slots and self.base_discount > 0:
            time_slots.append(TimeSlot(0, 24, ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday'], self.base_discount))
        
        return time_slots

    def _parse_days(self, days_text: str) -> List[str]:
        """Convert Hebrew day ranges to list of English day names."""
        day_map = {
            'א': 'Sunday',
            'ב': 'Monday',
            'ג': 'Tuesday',
            'ד': 'Wednesday',
            'ה': 'Thursday',
            'ו': 'Friday',
            'ש': 'Saturday'
        }
        
        days_text = days_text.replace("'", "").strip()
        
        if '-' in days_text:
            start, end = [d.strip() for d in days_text.split('-')]
            try:
                start_idx = list(day_map.keys()).index(start)
                end_idx = list(day_map.keys()).index(end)
                return [day_map[day] for day in list(day_map.keys())[start_idx:end_idx+1]]
            except ValueError:
                return [day_map[day] for day in ['א', 'ב', 'ג', 'ד', 'ה']]
        return [day_map[day] for day in days_text if day in day_map]

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary for DataFrame creation."""
        time_slot_details = []
        for slot in self.time_slots:
            time_slot_details.append({
                'start_hour': slot.start_hour,
                'end_hour': slot.end_hour,
                'days': ','.join(slot.days),
                'discount': slot.discount
            })
        
        return {
            'company': self.company,
            'plan_name': self.name,
            'description': self.description,
            'base_discount': self.base_discount,
            'requires_smart_meter': self.requires_smart_meter,
            'has_fixed_price': self.has_fixed_price,
            'has_online_management': self.has_online_management,
            'time_slots': len(self.time_slots),
            'time_slot_details': time_slot_details,
            'max_discount': max([slot.discount for slot in self.time_slots], default=self.base_discount),
            'avg_discount': np.mean([slot.discount for slot in self.time_slots]) if self.time_slots else self.base_discount,
            'covers_night_hours': any(slot.start_hour >= 23 or slot.end_hour <= 7 for slot in self.time_slots),
            'covers_day_hours': any(7 <= slot.start_hour <= 17 for slot in self.time_slots),
            'covers_weekend': any('Saturday' in slot.days for slot in self.time_slots)
        }

def process_plans(json_file: str) -> pd.DataFrame:
    """Process electricity plans from JSON file into a detailed DataFrame."""
    with open(json_file, 'r', encoding='utf-8') as f:
        raw_plans = json.load(f)
    
    plans = [ElectricityPlan(plan) for plan in raw_plans]
    plan_dicts = [plan.to_dict() for plan in plans]
    
    df = pd.DataFrame(plan_dicts)
    
    df['discount_score'] = df['max_discount'] * 0.7 + df['avg_discount'] * 0.3
    df['flexibility_score'] = (
        df['time_slots'] * 0.3 +
        df['covers_night_hours'].astype(int) * 0.3 +
        df['covers_day_hours'].astype(int) * 0.2 +
        df['covers_weekend'].astype(int) * 0.2
    )
    
    return df

def analyze_plans(df: pd.DataFrame) -> None:
    """Print analysis of the plans."""
    print(f"\nProcessed {len(df)} plans")
    
    print("\nTop 5 plans by discount score:")
    print(df.sort_values('discount_score', ascending=False)[
        ['company', 'plan_name', 'base_discount', 'max_discount', 'discount_score']
    ].head())
    
    print("\nTop 5 plans by flexibility score:")
    print(df.sort_values('flexibility_score', ascending=False)[
        ['company', 'plan_name', 'time_slots', 'flexibility_score']
    ].head())
    
    print("\nPlans with night hours coverage:")
    print(df[df['covers_night_hours']][
        ['company', 'plan_name', 'max_discount', 'time_slot_details']
    ].head())

if __name__ == "__main__":
    json_file = "electricity_plans_20250416_212107.json"
    df = process_plans(json_file)
    analyze_plans(df) 