import json
import pandas as pd
import numpy as np
from datetime import datetime, time
import re
import logging
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
from io import BytesIO
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimeSlot:
    def __init__(self, start_time: str, end_time: str, discount: float, days: List[str] = None):
        self.start_time = self._parse_time(start_time)
        self.end_time = self._parse_time(end_time)
        self.discount = discount
        self.days = days or ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string in format HH:MM to time object."""
        try:
            return datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            logger.error(f"Invalid time format: {time_str}")
            return time(0, 0)
    
    def is_active(self, dt: datetime) -> bool:
        """Check if the time slot is active for the given datetime."""
        if dt.strftime('%A') not in self.days:
            return False
        
        current_time = dt.time()
        if self.start_time <= self.end_time:
            return self.start_time <= current_time <= self.end_time
        else:  # Handle overnight slots (e.g., 23:00-07:00)
            return current_time >= self.start_time or current_time <= self.end_time

class ElectricityPlan:
    def __init__(self, raw_data: Dict):
        self.company = raw_data.get('company', 'Unknown')
        self.name = raw_data.get('name', 'Unknown')
        self.description = raw_data.get('description', '')
        self.features = raw_data.get('features', [])
        self.base_rate = raw_data.get('base_rate', 0.0)
        self.monthly_fee = raw_data.get('monthly_fee', 0.0)
        self.time_slots = self._parse_time_slots(raw_data)
        self.requires_smart_meter = any('מונה חכם' in feature for feature in self.features)
    
    def _parse_time_slots(self, raw_data: Dict) -> List[TimeSlot]:
        """Parse time slots from plan data."""
        time_slots = []
        
        # Extract base discount
        base_discount = self._extract_discount(raw_data.get('discount', '0%'))
        
        # Parse time slots from description and features
        time_pattern = r'(\d{1,2}:\d{2})'
        
        # Check description for time slots
        desc_times = re.findall(time_pattern, self.description)
        if len(desc_times) >= 2:
            time_slots.append(TimeSlot(desc_times[0], desc_times[1], base_discount))
        
        # Check features for time slots
        for feature in self.features:
            feature_times = re.findall(time_pattern, feature)
            if len(feature_times) >= 2:
                discount = self._extract_discount(feature) or base_discount
                time_slots.append(TimeSlot(feature_times[0], feature_times[1], discount))
        
        # If no time slots found, create a default one with base discount
        if not time_slots:
            time_slots.append(TimeSlot('00:00', '23:59', base_discount))
        
        return time_slots
    
    def _extract_discount(self, text: str) -> float:
        """Extract discount percentage from text."""
        if not text:
            return 0.0
        
        match = re.search(r'(\d+(?:\.\d+)?)%', text)
        if match:
            return float(match.group(1)) / 100
        return 0.0
    
    def calculate_cost(self, consumption_data: pd.DataFrame) -> Tuple[float, float]:
        """Calculate the total cost and savings for this plan."""
        total_cost = 0.0
        total_consumption = 0.0
        
        for _, row in consumption_data.iterrows():
            consumption = row['usage']
            dt = row['datetime']
            
            # Find applicable discount
            discount = 0.0
            for slot in self.time_slots:
                if slot.is_active(dt):
                    discount = max(discount, slot.discount)
            
            # Calculate cost for this hour
            hourly_cost = consumption * self.base_rate * (1 - discount)
            total_cost += hourly_cost
            total_consumption += consumption
        
        # Add monthly fees
        months = len(consumption_data['datetime'].dt.to_period('M').unique())
        total_cost += self.monthly_fee * months
        
        # Calculate IEC cost (basic rate without discounts)
        iec_cost = total_consumption * 0.5425  # Basic IEC rate
        
        # Calculate savings
        savings = iec_cost - total_cost
        
        return total_cost, savings

def analyze_plans(consumption_data: pd.DataFrame, plans_file: str = 'electricity_plans_20250421_223808.json') -> Dict:
    """Analyze electricity plans and compare with IEC basic rates."""
    try:
        # Load plans
        with open(plans_file, 'r', encoding='utf-8') as f:
            raw_plans = json.load(f)
        
        # Process plans
        plans = [ElectricityPlan(plan) for plan in raw_plans]
        
        # Calculate costs for each plan
        plan_comparisons = []
        for plan in plans:
            try:
                total_cost, savings = plan.calculate_cost(consumption_data)
                savings_percentage = (savings / total_cost) * 100 if total_cost > 0 else 0
                
                plan_comparisons.append({
                    'plan_name': plan.name,
                    'provider': plan.company,
                    'annual_cost': total_cost,
                    'savings': savings,
                    'savings_percentage': savings_percentage,
                    'requires_smart_meter': plan.requires_smart_meter
                })
            except Exception as e:
                logger.error(f"Error analyzing plan {plan.name}: {str(e)}")
                continue
        
        # Sort plans by savings
        plan_comparisons.sort(key=lambda x: x['savings'], reverse=True)
        
        # Generate visualization
        plt.figure(figsize=(12, 6))
        top_plans = plan_comparisons[:5]  # Show top 5 plans
        x = range(len(top_plans))
        width = 0.35
        
        plt.bar(x, [p['annual_cost'] for p in top_plans], width, label='Plan Cost')
        plt.bar([i + width for i in x], [p['savings'] for p in top_plans], width, label='Savings')
        
        plt.xlabel('Electricity Plans')
        plt.ylabel('Amount (NIS)')
        plt.title('Top 5 Cost-Saving Electricity Plans')
        plt.xticks([i + width/2 for i in x], [p['plan_name'] for p in top_plans], rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        
        # Convert plot to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        buffer.seek(0)
        plt.close()
        
        return {
            'plot': base64.b64encode(buffer.getvalue()).decode(),
            'comparisons': plan_comparisons
        }
        
    except Exception as e:
        logger.error(f"Error analyzing plans: {str(e)}")
        return None 