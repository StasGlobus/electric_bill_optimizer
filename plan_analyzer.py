import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, time, timedelta
import json
import os
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import re
import random
import pytz

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure matplotlib for Hebrew support
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['axes.unicode_minus'] = False

# Israel timezone
ISRAEL_TZ = pytz.timezone('Asia/Jerusalem')

@dataclass
class TimeSlot:
    start_time: time
    end_time: time
    discount: float

@dataclass
class PlanCost:
    company: str
    plan_name: str
    total_cost: float
    savings: float
    savings_percentage: float
    time_slots: List[Dict]

class ElectricityPlanAnalyzer:
    def __init__(self, consumption_data_path='input_example.csv', output_dir='output'):
        """Initialize the analyzer with consumption data and output directory."""
        self.consumption_data_path = consumption_data_path
        self.output_dir = output_dir
        self.consumption_data = None
        self.base_rate = 0.0
        self.fixed_distribution = 0.0
        self.fixed_supply = 0.0
        self.base_total_cost = 0.0
        self.load_consumption_data()
        self.calculate_base_costs()

    def load_consumption_data(self):
        """Load and process consumption data."""
        print("Loading consumption data...")
        self.consumption_data = pd.read_csv(self.consumption_data_path, encoding='utf-8')
        print(f"Initial data shape: {self.consumption_data.shape}")
        print(f"Initial columns: {self.consumption_data.columns.tolist()}")
        
        print("Processing datetime...")
        # Combine date and time columns into datetime
        self.consumption_data['datetime'] = pd.to_datetime(
            self.consumption_data['תאריך'] + ' ' + self.consumption_data['מועד תחילת הפעימה'],
            format='%d/%m/%Y %H:%M',
            errors='coerce'
        )
        
        # Remove any rows where datetime conversion failed
        self.consumption_data = self.consumption_data.dropna(subset=['datetime'])
        print(f"Rows after datetime conversion: {len(self.consumption_data)}")
        
        # Convert to Israel timezone, handling DST transitions
        def handle_dst(dt):
            try:
                return ISRAEL_TZ.localize(dt, is_dst=None)
            except pytz.exceptions.AmbiguousTimeError:
                # During DST transition, use the earlier time
                return ISRAEL_TZ.localize(dt, is_dst=True)
            except pytz.exceptions.NonExistentTimeError:
                # For non-existent times (spring forward), shift forward by 1 hour
                return ISRAEL_TZ.localize(dt + pd.Timedelta(hours=1), is_dst=True)
        
        # Apply timezone conversion
        self.consumption_data['datetime'] = self.consumption_data['datetime'].apply(handle_dst)
        print(f"Timezone conversion completed. Sample times: {self.consumption_data['datetime'].iloc[0]} to {self.consumption_data['datetime'].iloc[-1]}")
        
        # Clean up the data - remove empty rows and reset index
        self.consumption_data = self.consumption_data.dropna(how='all').reset_index(drop=True)
        
        # Rename consumption column
        self.consumption_data = self.consumption_data.rename(columns={'צריכה בקוט"ש': 'consumption'})
        
        # Convert consumption to numeric, replacing any non-numeric values with NaN
        self.consumption_data['consumption'] = pd.to_numeric(self.consumption_data['consumption'], errors='coerce')
        
        # Remove rows with invalid consumption values
        self.consumption_data = self.consumption_data.dropna(subset=['consumption'])
        print(f"Final data shape: {self.consumption_data.shape}")
        print(f"Data types:\n{self.consumption_data.dtypes}")

    def calculate_base_costs(self):
        """Calculate base costs using IEC tariffs."""
        try:
            # Calculate total consumption
            total_consumption = self.consumption_data['consumption'].sum()
            
            # Calculate number of months
            date_range = pd.date_range(
                start=self.consumption_data['datetime'].min(),
                end=self.consumption_data['datetime'].max(),
                freq='M'
            )
            num_months = len(date_range)
            
            # Set base rates (from IEC tariffs)
            self.base_rate = 0.5425  # Base rate per kWh
            self.fixed_distribution = 9.60 * num_months  # Monthly fixed distribution fee
            self.fixed_supply = 13.37 * num_months  # Monthly fixed supply fee
            
            # Calculate total base cost
            consumption_cost = total_consumption * self.base_rate
            total_cost = consumption_cost + self.fixed_distribution + self.fixed_supply
            self.base_total_cost = total_cost * 1.17  # Add VAT
            
            print(f"Date range: {date_range[0]} to {date_range[-1]}")
            print(f"Number of months: {num_months}")
            print(f"Total consumption: {total_consumption:.2f} kWh")
            print(f"Consumption cost: ₪{consumption_cost:.2f}")
            print(f"Fixed costs: ₪{self.fixed_distribution + self.fixed_supply:.2f}")
            print(f"Total cost with VAT: ₪{self.base_total_cost:.2f}")
            
        except Exception as e:
            print(f"Error calculating base costs: {str(e)}")

    def _parse_time_slot(self, slot_str: str) -> Optional[TimeSlot]:
        try:
            if not slot_str or slot_str.lower() == 'all day':
                return TimeSlot(time(0, 0), time(23, 59), 0)
            
            start_str, end_str = slot_str.split('-')
            start_time = datetime.strptime(start_str.strip(), '%H:%M').time()
            end_time = datetime.strptime(end_str.strip(), '%H:%M').time()
            
            return TimeSlot(start_time, end_time, 0)
        except Exception:
            return None

    def _is_in_time_slot(self, dt: datetime, slot: TimeSlot) -> bool:
        current_time = dt.time()
        if slot.start_time <= slot.end_time:
            return slot.start_time <= current_time <= slot.end_time
        else:  # Handle overnight slots (e.g., 22:00-06:00)
            return current_time >= slot.start_time or current_time <= slot.end_time

    def calculate_plan_cost(self, plan):
        try:
            if not plan or not isinstance(plan, dict):
                return None

            # Extract plan data
            company = plan.get('company', 'Unknown')
            plan_name = plan.get('name', 'Unknown')
            description = plan.get('description', '')
            features = plan.get('features', [])
            
            # Convert discount from string to float
            discount_str = plan.get('discount', '0%')
            try:
                # Remove % sign and convert to decimal
                discount = float(discount_str.strip('%')) / 100
            except (ValueError, AttributeError):
                discount = 0.0

            # Extract time slots from description and features
            time_slots = []
            time_pattern = r'(\d{1,2}:\d{2})'
            
            # Search in description
            desc_times = re.findall(time_pattern, description)
            if len(desc_times) >= 2:
                time_slots.append({
                    'start_time': desc_times[0],
                    'end_time': desc_times[1],
                    'discount': discount
                })
            
            # Search in features
            for feature in features:
                feature_times = re.findall(time_pattern, feature)
                if len(feature_times) >= 2:
                    time_slots.append({
                        'start_time': feature_times[0],
                        'end_time': feature_times[1],
                        'discount': discount
                    })

            # If no time slots found, apply discount to all hours
            if not time_slots:
                time_slots = [{
                    'start_time': '00:00',
                    'end_time': '23:59',
                    'discount': discount
                }]

            # Calculate costs
            total_consumption_cost = 0
            regular_consumption = 0
            discounted_consumption = 0

            for _, row in self.consumption_data.iterrows():
                consumption = row['consumption']
                time = row['datetime'].strftime('%H:%M')
                
                # Check if time falls within any discount period
                has_discount = False
                for slot in time_slots:
                    if slot['start_time'] <= time <= slot['end_time']:
                        has_discount = True
                        break
                
                if has_discount:
                    discounted_consumption += consumption
                else:
                    regular_consumption += consumption

            # Calculate consumption costs using IEC tariffs
            total_consumption_cost = (
                regular_consumption * self.base_rate +
                discounted_consumption * self.base_rate * (1 - discount)
            )

            # Add fixed costs
            total_cost = (total_consumption_cost + self.fixed_distribution + self.fixed_supply) * 1.17  # Add VAT

            # Calculate savings
            savings = self.base_total_cost - total_cost
            savings_percentage = (savings / self.base_total_cost) * 100 if self.base_total_cost > 0 else 0

            # Validate output types
            if not isinstance(total_cost, (int, float)):
                total_cost = float(total_cost)
            if not isinstance(savings, (int, float)):
                savings = float(savings)
            if not isinstance(savings_percentage, (int, float)):
                savings_percentage = float(savings_percentage)

            return PlanCost(
                company=company,
                plan_name=plan_name,
                total_cost=total_cost,
                savings=savings,
                savings_percentage=savings_percentage,
                time_slots=time_slots
            )
        except Exception as e:
            print(f"Error calculating plan cost: {str(e)}")
            return None

    def analyze_all_plans(self) -> List[PlanCost]:
        """Analyze all electricity plans and return sorted results by savings."""
        print("Loading plans...")
        plans = load_latest_plans()
        print(f"Found {len(plans)} plans to analyze")
        
        # Calculate metadata
        total_plans = len(plans)
        valid_plans = 0
        invalid_plans = 0
        
        plan_costs = []
        for i, plan in enumerate(plans, 1):
            print(f"\nProcessing plan {i}/{total_plans}:")
            print(f"Company: {plan.get('company', 'Unknown')}")
            print(f"Plan name: {plan.get('plan_name', 'Unknown')}")
            
            cost_analysis = self.calculate_plan_cost(plan)
            if cost_analysis:
                plan_costs.append(cost_analysis)
                valid_plans += 1
            else:
                invalid_plans += 1
        
        print(f"\nAnalysis summary:")
        print(f"Total plans processed: {total_plans}")
        print(f"Valid plans: {valid_plans}")
        print(f"Invalid plans: {invalid_plans}")
        print(f"Successfully analyzed {len(plan_costs)} plans")
        
        return sorted(plan_costs, key=lambda x: x.savings_percentage, reverse=True)

    def generate_visualizations(self, plan_costs: List[PlanCost]) -> None:
        """Generate all visualizations for the report."""
        print("Generating visualizations...")
        self._generate_consumption_visualizations()
        self._generate_cost_comparison(plan_costs)

    def _generate_consumption_visualizations(self) -> None:
        # Daily consumption
        plt.figure(figsize=(15, 6))
        self.consumption_data.groupby(self.consumption_data['datetime'].dt.date)['consumption'].sum().plot()
        plt.title('Daily Electricity Consumption')
        plt.xlabel('Date')
        plt.ylabel('Consumption (kWh)')
        plt.grid(True)
        plt.savefig(os.path.join(self.output_dir, 'daily_consumption.png'))
        plt.close()

        # Monthly consumption
        plt.figure(figsize=(10, 6))
        monthly = self.consumption_data.groupby(self.consumption_data['datetime'].dt.month)['consumption'].sum()
        monthly.plot(kind='bar')
        plt.title('Monthly Electricity Consumption')
        plt.xlabel('Month')
        plt.ylabel('Consumption (kWh)')
        plt.grid(True)
        plt.savefig(os.path.join(self.output_dir, 'monthly_consumption.png'))
        plt.close()

        # Hourly patterns - circular visualization
        fig = plt.figure(figsize=(12, 10))
        
        # Create subplot with space for colorbar
        gs = plt.GridSpec(1, 2, width_ratios=[4, 0.2])
        ax = plt.subplot(gs[0], projection='polar')
        
        # Get hourly data
        hourly = self.consumption_data.groupby(self.consumption_data['datetime'].dt.hour)['consumption'].mean()
        
        # Convert hours to angles (in radians)
        theta = np.linspace(0, 2*np.pi, 24, endpoint=False)
        
        # Create color gradient based on consumption values
        norm = plt.Normalize(hourly.min(), hourly.max())
        cmap = plt.cm.viridis
        colors = cmap(norm(hourly.values))
        
        # Plot bars
        width = 2*np.pi/24  # Width of each bar
        bars = ax.bar(theta, hourly.values, width=width, color=colors, alpha=0.7)
        
        # Customize the plot
        ax.set_theta_direction(-1)  # Clockwise
        ax.set_theta_zero_location('N')  # 0 at the top (midnight)
        
        # Set custom tick labels
        ax.set_xticks(theta)
        ax.set_xticklabels([f'{h:02d}:00' for h in range(24)])
        
        # Add colorbar
        cax = plt.subplot(gs[1])
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        plt.colorbar(sm, cax=cax, label='Average Consumption (kWh)')
        
        # Add title
        plt.suptitle('24-Hour Electricity Consumption Pattern (Israel Time)', y=1.05)
        
        # Add night period shading (23:00-07:00)
        night_theta = np.linspace(23/12*np.pi, 7/12*np.pi, 100)
        ax.fill_between(night_theta, 0, hourly.max()*1.1, color='blue', alpha=0.1, label='Night (23:00-07:00)')
        
        # Add legend
        ax.legend(loc='center left', bbox_to_anchor=(1.2, 0.5))
        
        # Save the plot
        plt.savefig(os.path.join(self.output_dir, 'hourly_patterns.png'), bbox_inches='tight', dpi=300)
        plt.close()

    def _generate_cost_comparison(self, plan_costs: List[PlanCost]) -> None:
        plt.figure(figsize=(15, 8))
        
        companies = [f"{pc.company}\n{pc.plan_name}" for pc in plan_costs]
        costs = [pc.total_cost for pc in plan_costs]
        savings = [pc.savings for pc in plan_costs]
        
        x = np.arange(len(companies))
        width = 0.35
        
        plt.bar(x - width/2, costs, width, label='Total Cost')
        plt.bar(x + width/2, savings, width, label='Savings')
        
        plt.title('Electricity Plan Cost Comparison')
        plt.xlabel('Plan')
        plt.ylabel('Amount (₪)')
        plt.xticks(x, companies, rotation=45, ha='right')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'plan_comparison.png'))
        plt.close()

    def generate_report(self, plan_costs):
        """Generate a comprehensive report of the analysis"""
        try:
            report = []
            report.append("# Electricity Plan Analysis Report\n")
            
            # Add consumption statistics
            report.append("## Consumption Statistics\n")
            stats = self.generate_eda_statistics()
            report.extend([f"- {k}: {v}" for k, v in stats.items()])
            report.append("")
            
            # Add cost analysis
            report.append("## Cost Analysis\n")
            report.append(f"- Base cost (IEC): ₪{self.base_total_cost:.2f}")
            report.append("")
            
            # Add plan recommendations
            report.append("## Plan Recommendations\n")
            for i, cost in enumerate(sorted(plan_costs, key=lambda x: x.total_cost), 1):
                report.append(f"\n{i}. {cost.company} - {cost.plan_name}")
                report.append(f"   Cost: ₪{cost.total_cost:.2f}")
                report.append(f"   Savings: ₪{cost.savings:.2f} ({cost.savings_percentage:.1f}%)")
                report.append("   Discount Periods:")
                for slot in cost.time_slots:
                    report.append(f"   - {slot['start_time']} to {slot['end_time']}: {slot['discount']*100:.0f}%")
            
            # Add visualization references
            report.append("\n## Visualizations")
            report.append("Generated visualizations:")
            report.append("- Daily consumption pattern: daily_consumption.png")
            report.append("- Monthly consumption pattern: monthly_consumption.png")
            report.append("- Hourly consumption pattern: hourly_consumption.png")
            report.append("- Cost comparison: cost_comparison.png")
            
            return "\n".join(report)
        except Exception as e:
            print(f"Error generating report: {str(e)}")
            return ""

    def save_report(self, report_content):
        """Save the report to a file."""
        try:
            if not report_content:
                raise ValueError("Report content is empty")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(self.output_dir, f"analysis_report_{timestamp}.txt")
            
            os.makedirs(self.output_dir, exist_ok=True)
            with open(report_file, 'w', encoding='utf-8-sig') as f:
                f.write(report_content)
            
            print(f"Report saved as {os.path.basename(report_file)}")
        except Exception as e:
            print(f"Error saving report: {str(e)}")

    def generate_eda_statistics(self):
        """Generate exploratory data analysis statistics."""
        try:
            stats = {}
            
            # Total consumption
            total_consumption = self.consumption_data['consumption'].sum()
            stats['Total Consumption'] = f"{total_consumption:.2f} kWh"
            
            # Daily average
            daily_avg = self.consumption_data.groupby(self.consumption_data['datetime'].dt.date)['consumption'].sum().mean()
            stats['Average Daily Consumption'] = f"{daily_avg:.2f} kWh"
            
            # Peak hour
            peak_hour = self.consumption_data.groupby(self.consumption_data['datetime'].dt.hour)['consumption'].mean().idxmax()
            stats['Peak Hour (Israel Time)'] = f"{peak_hour:02d}:00"
            
            # Monthly consumption
            monthly_consumption = self.consumption_data.groupby(self.consumption_data['datetime'].dt.to_period('M'))['consumption'].sum()
            stats['Highest Monthly Consumption'] = f"{monthly_consumption.max():.2f} kWh ({monthly_consumption.idxmax()})"
            stats['Lowest Monthly Consumption'] = f"{monthly_consumption.min():.2f} kWh ({monthly_consumption.idxmin()})"
            
            # Day/Night consumption
            night_mask = (self.consumption_data['datetime'].dt.hour >= 23) | (self.consumption_data['datetime'].dt.hour < 7)
            night_consumption = self.consumption_data[night_mask]['consumption'].sum()
            day_consumption = self.consumption_data[~night_mask]['consumption'].sum()
            stats['Night Consumption (23:00-07:00)'] = f"{night_consumption:.2f} kWh ({(night_consumption/total_consumption*100):.1f}%)"
            stats['Day Consumption (07:00-23:00)'] = f"{day_consumption:.2f} kWh ({(day_consumption/total_consumption*100):.1f}%)"
            
            return stats
        except Exception as e:
            print(f"Error generating statistics: {str(e)}")
            return {}

def load_latest_plans() -> List[Dict]:
    """Load the most recent electricity plans from JSON files."""
    try:
        plan_files = [f for f in os.listdir() if f.startswith('electricity_plans_') and f.endswith('.json')]
        if not plan_files:
            print("No plan files found")
            return []
        
        latest_file = max(plan_files)
        print(f"Loading plans from {latest_file}")
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading plans: {e}")
        return []

def main():
    """Main function to run the analyzer."""
    try:
        print("Starting analysis...")
        analyzer = ElectricityPlanAnalyzer()
        plan_costs = analyzer.analyze_all_plans()
        
        if plan_costs:
            # Generate visualizations
            analyzer.generate_visualizations(plan_costs)
            
            # Generate and save report
            report = analyzer.generate_report(plan_costs)
            analyzer.save_report(report)
            print("Analysis completed successfully")
        else:
            print("No valid plans found for analysis")
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 