import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import csv
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List
import threading
import queue

# Simple pandas replacement for basic operations
class SimpleDataFrame:
    def __init__(self, data):
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            self.data = data
            self.columns = list(data[0].keys()) if data else []
        else:
            self.data = []
            self.columns = []
    
    def groupby(self, column):
        groups = {}
        for row in self.data:
            key = row[column]
            if key not in groups:
                groups[key] = []
            groups[key].append(row)
        return SimpleGroupBy(groups)
    
    def __getitem__(self, key):
        if isinstance(key, str):
            return [row[key] for row in self.data]
        elif isinstance(key, list):
            result = []
            for row in self.data:
                new_row = {k: row[k] for k in key if k in row}
                result.append(new_row)
            return SimpleDataFrame(result)
    
    def to_csv(self, filename, index=False):
        if not self.data:
            return
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.columns)
            writer.writeheader()
            writer.writerows(self.data)

class SimpleGroupBy:
    def __init__(self, groups):
        self.groups = groups
    
    def agg(self, agg_dict):
        result = {}
        for group_key, group_data in self.groups.items():
            result[group_key] = {}
            for column, funcs in agg_dict.items():
                if isinstance(funcs, str):
                    funcs = [funcs]
                for func in funcs:
                    values = [row[column] for row in group_data]
                    if func == 'mean':
                        result[group_key][f"{column}_{func}"] = sum(values) / len(values)
                    elif func == 'std':
                        mean_val = sum(values) / len(values)
                        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
                        result[group_key][f"{column}_{func}"] = variance ** 0.5
                    elif func == 'min':
                        result[group_key][f"{column}_{func}"] = min(values)
                    elif func == 'max':
                        result[group_key][f"{column}_{func}"] = max(values)
        return result

# Configure matplotlib
plt.style.use('default')
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = "#d4d8db"
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['font.size'] = 9

@dataclass
class BusinessParameters:
    base_revenue: float
    base_costs: float
    num_employees: int
    avg_employee_salary: float
    baseline_growth_rate: float
    simulation_years: int

@dataclass
class StrategicDecisions:
    staff_to_hire: int = 0
    expand_new_region: bool = False
    automation_percentage: float = 0.0
    marketing_spend: float = 0.0

@dataclass
class MarketScenario:
    name: str
    description: str
    growth_modifier: float
    cost_modifier: float
    volatility: float

DEFAULT_SCENARIOS = [
    MarketScenario("Recession", "Economic downturn", 0.3, 1.1, 0.15),
    MarketScenario("Stagnation", "Flat market", 0.7, 1.05, 0.08),
    MarketScenario("Normal Growth", "Stable conditions", 1.0, 1.0, 0.05),
    MarketScenario("Growth Phase", "Expanding market", 1.4, 0.95, 0.08),
    MarketScenario("Boom", "Rapid expansion", 1.8, 0.9, 0.12)
]

class DecisionImpactCalculator:
    def __init__(self):
        self.HIRING_GROWTH_MULTIPLIER = 0.0015  # Reduced from 0.015 to 0.0015 (0.15% per employee)
        self.EXPANSION_GROWTH_BOOST = 0.02      # Reduced from 0.12 to 0.02 (2%)
        self.EXPANSION_COST_MULTIPLIER = 0.25
        self.EXPANSION_RISK_FACTOR = 0.08
        self.AUTOMATION_COST_REDUCTION = 0.003
        self.AUTOMATION_PRODUCTIVITY_BOOST = 0.0001  # Reduced from 0.001 to 0.0001
        self.MARKETING_ROI = 0.0000002  # Reduced from 0.000002 to 0.0000002
    
    def calculate_impacts(self, decisions: StrategicDecisions, base_params: BusinessParameters) -> Dict:
        impacts = {
            'growth_rate_adjustment': 0.0,
            'cost_adjustment': 0.0,
            'risk_factor': 0.0,
            'breakdown': {
                'hiring': {'growth': 0.0, 'cost': 0.0},
                'expansion': {'growth': 0.0, 'cost': 0.0, 'risk': 0.0},
                'automation': {'growth': 0.0, 'cost': 0.0},
                'marketing': {'growth': 0.0, 'cost': 0.0}
            }
        }
        
        # Staff hiring - now uses the user-defined average salary
        if decisions.staff_to_hire > 0:
            growth_impact = decisions.staff_to_hire * self.HIRING_GROWTH_MULTIPLIER
            cost_impact = decisions.staff_to_hire * base_params.avg_employee_salary
            impacts['growth_rate_adjustment'] += growth_impact
            impacts['cost_adjustment'] += cost_impact
            impacts['breakdown']['hiring'] = {'growth': growth_impact, 'cost': cost_impact}
        
        # Expansion
        if decisions.expand_new_region:
            growth_impact = self.EXPANSION_GROWTH_BOOST
            cost_impact = base_params.base_costs * self.EXPANSION_COST_MULTIPLIER
            risk_impact = self.EXPANSION_RISK_FACTOR
            impacts['growth_rate_adjustment'] += growth_impact
            impacts['cost_adjustment'] += cost_impact
            impacts['risk_factor'] = risk_impact
            impacts['breakdown']['expansion'] = {'growth': growth_impact, 'cost': cost_impact, 'risk': risk_impact}
        
        # Automation
        if decisions.automation_percentage > 0:
            cost_impact = -base_params.base_costs * (decisions.automation_percentage / 100) * self.AUTOMATION_COST_REDUCTION
            growth_impact = (decisions.automation_percentage / 100) * self.AUTOMATION_PRODUCTIVITY_BOOST
            impacts['cost_adjustment'] += cost_impact
            impacts['growth_rate_adjustment'] += growth_impact
            impacts['breakdown']['automation'] = {'growth': growth_impact, 'cost': cost_impact}
        
        # Marketing
        if decisions.marketing_spend > 0:
            growth_impact = decisions.marketing_spend * self.MARKETING_ROI
            cost_impact = decisions.marketing_spend
            impacts['growth_rate_adjustment'] += growth_impact
            impacts['cost_adjustment'] += cost_impact
            impacts['breakdown']['marketing'] = {'growth': growth_impact, 'cost': cost_impact}
        
        return impacts

class MonteCarloSimulator:
    def __init__(self, num_simulations: int = 500):
        self.num_simulations = num_simulations
        self.impact_calculator = DecisionImpactCalculator()
    
    def run_simulation(self, base_params: BusinessParameters, decisions: StrategicDecisions, 
                      progress_callback=None) -> SimpleDataFrame:
        impacts = self.impact_calculator.calculate_impacts(decisions, base_params)
        adjusted_growth_rate = base_params.baseline_growth_rate + impacts['growth_rate_adjustment']
        adjusted_base_costs = base_params.base_costs + impacts['cost_adjustment']
        risk_factor = max(0.01, impacts['risk_factor'])  # Minimum baseline risk
        
        results = []
        
        for sim in range(self.num_simulations):
            if progress_callback and sim % 50 == 0:
                progress_callback(sim / self.num_simulations * 100)
            
            current_revenue = base_params.base_revenue
            current_costs = adjusted_base_costs
            
            for year in range(base_params.simulation_years + 1):
                if year == 0:
                    net_profit = current_revenue - current_costs
                    profit_margin = (net_profit / current_revenue) * 100 if current_revenue > 0 else 0
                    results.append({
                        'Year': year, 'Revenue': current_revenue, 'Costs': current_costs,
                        'Net_Profit': net_profit, 'Profit_Margin': profit_margin, 'Simulation': sim
                    })
                else:
                    # Add market volatility
                    growth_variation = np.random.normal(0, risk_factor)
                    actual_growth_rate = adjusted_growth_rate + growth_variation
                    
                    # Apply growth with some cost scaling
                    current_revenue *= (1 + actual_growth_rate)
                    current_costs *= (1 + max(0, actual_growth_rate * 0.6))
                    
                    net_profit = current_revenue - current_costs
                    profit_margin = (net_profit / current_revenue) * 100 if current_revenue > 0 else 0
                    results.append({
                        'Year': year, 'Revenue': current_revenue, 'Costs': current_costs,
                        'Net_Profit': net_profit, 'Profit_Margin': profit_margin, 'Simulation': sim
                    })
        
        if progress_callback:
            progress_callback(100)
        
        return SimpleDataFrame(results)
    
    def run_scenario_analysis(self, base_params: BusinessParameters, decisions: StrategicDecisions, 
                            scenarios: List[MarketScenario], progress_callback=None) -> Dict[str, SimpleDataFrame]:
        all_results = {}
        total_scenarios = len(scenarios)
        
        for i, scenario in enumerate(scenarios):
            if progress_callback:
                progress_callback(f"Running {scenario.name} scenario...", (i / total_scenarios) * 100)
            
            scenario_params = self._apply_scenario_to_params(base_params, scenario)
            results = self.run_simulation(scenario_params, decisions, 
                                        lambda p: progress_callback(
                                            f"Running {scenario.name} scenario... {p:.0f}%",
                                            (i / total_scenarios) * 100 + (p / total_scenarios)
                                        ) if progress_callback else None)
            
            for row in results.data:
                row['Scenario'] = scenario.name
                row['Scenario_Description'] = scenario.description
            
            all_results[scenario.name] = results
        
        if progress_callback:
            progress_callback("Analysis complete!", 100)
        
        return all_results
    
    def _apply_scenario_to_params(self, base_params: BusinessParameters, scenario: MarketScenario) -> BusinessParameters:
        adjusted_growth = base_params.baseline_growth_rate * scenario.growth_modifier
        adjusted_costs = base_params.base_costs * scenario.cost_modifier
        
        return BusinessParameters(
            base_revenue=base_params.base_revenue,
            base_costs=adjusted_costs,
            num_employees=base_params.num_employees,
            avg_employee_salary=base_params.avg_employee_salary,
            baseline_growth_rate=adjusted_growth,
            simulation_years=base_params.simulation_years
        )

class BusinessSimulatorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Business Growth Simulator")
        self.root.geometry("1400x900")
        self.root.configure(bg="#f0f0f0")
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.current_results = None
        self.current_impacts = None
        self.current_base_params = None
        self.current_decisions = None
        
        self.create_widgets()
        self.simulator = MonteCarloSimulator()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        title_label = ttk.Label(main_frame, text="Business Growth Simulator", font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.create_input_tab()
        self.create_results_tab()
        self.create_summary_tab()
    
    def create_input_tab(self):
        input_frame = ttk.Frame(self.notebook)
        self.notebook.add(input_frame, text="Parameters & Decisions")
        
        # Create main horizontal layout
        main_horizontal_frame = ttk.Frame(input_frame)
        main_horizontal_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Parameters (scrollable)
        left_frame = ttk.Frame(main_horizontal_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        canvas = tk.Canvas(left_frame, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mouse wheel to canvas for scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Right side - Growth Rate Calculators
        right_frame = ttk.Frame(main_horizontal_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        self.create_left_side_content(scrollable_frame)
        self.create_growth_calculators(right_frame)
    
    def create_left_side_content(self, parent):
        # Base Parameters
        base_frame = ttk.LabelFrame(parent, text="Base Business Parameters", padding=10)
        base_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(base_frame, text="Base Annual Revenue (£):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.revenue_var = tk.StringVar(value="1000000")
        ttk.Entry(base_frame, textvariable=self.revenue_var, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(base_frame, text="Base Annual Costs (£):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.costs_var = tk.StringVar(value="700000")
        ttk.Entry(base_frame, textvariable=self.costs_var, width=15).grid(row=1, column=1, padx=5)
        
        ttk.Label(base_frame, text="Current Employees:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.employees_var = tk.IntVar(value=50)
        ttk.Spinbox(base_frame, from_=1, to=10000, textvariable=self.employees_var, width=13).grid(row=2, column=1, padx=5)
        
        # Employee salary field
        ttk.Label(base_frame, text="Average Employee Salary (£):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.salary_var = tk.StringVar(value="55000")
        salary_entry = ttk.Entry(base_frame, textvariable=self.salary_var, width=15)
        salary_entry.grid(row=3, column=1, padx=5)
        salary_entry.bind('<KeyRelease>', self.update_staff_label_on_salary_change)
        
        ttk.Label(base_frame, text="Baseline Growth Rate (%):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.growth_var = tk.DoubleVar(value=5.0)
        growth_scale = ttk.Scale(base_frame, from_=-10, to=50, variable=self.growth_var, orient=tk.HORIZONTAL, length=200)
        growth_scale.grid(row=4, column=1, padx=5)
        self.growth_label = ttk.Label(base_frame, text="5.0%")
        self.growth_label.grid(row=4, column=2)
        growth_scale.configure(command=self.update_growth_label)
        
        ttk.Label(base_frame, text="Simulation Years:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.years_var = tk.IntVar(value=5)
        years_scale = ttk.Scale(base_frame, from_=1, to=15, variable=self.years_var, orient=tk.HORIZONTAL, length=200)
        years_scale.grid(row=5, column=1, padx=5)
        self.years_label = ttk.Label(base_frame, text="5 years")
        self.years_label.grid(row=5, column=2)
        years_scale.configure(command=self.update_years_label)
        
        # Strategic Decisions
        decisions_frame = ttk.LabelFrame(parent, text="Strategic Decisions", padding=10)
        decisions_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Staff hiring
        staff_frame = ttk.LabelFrame(decisions_frame, text="Staffing Strategy", padding=5)
        staff_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(staff_frame, text="Staff to Hire:").grid(row=0, column=0, sticky=tk.W)
        self.staff_var = tk.IntVar(value=0)
        staff_scale = ttk.Scale(staff_frame, from_=0, to=100, variable=self.staff_var, orient=tk.HORIZONTAL, length=200)
        staff_scale.grid(row=0, column=1, padx=5)
        self.staff_label = ttk.Label(staff_frame, text="0 staff")
        self.staff_label.grid(row=0, column=2)
        staff_scale.configure(command=self.update_staff_label)
        
        self.staff_impact_label = ttk.Label(staff_frame, text="Impact: No change", foreground='gray')
        self.staff_impact_label.grid(row=1, column=0, columnspan=3, sticky=tk.W)
        
        # Expansion
        expansion_frame = ttk.LabelFrame(decisions_frame, text="Market Expansion", padding=5)
        expansion_frame.pack(fill=tk.X, pady=5)
        
        self.expansion_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(expansion_frame, text="Expand to New Region", 
                       variable=self.expansion_var, command=self.update_expansion_label).pack(anchor=tk.W)
        
        self.expansion_impact_label = ttk.Label(expansion_frame, text="Impact: No expansion", foreground='gray')
        self.expansion_impact_label.pack(anchor=tk.W)
        
        # Automation
        automation_frame = ttk.LabelFrame(decisions_frame, text="Process Automation", padding=5)
        automation_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(automation_frame, text="Automation Level (%):").grid(row=0, column=0, sticky=tk.W)
        self.automation_var = tk.DoubleVar(value=0.0)
        automation_scale = ttk.Scale(automation_frame, from_=0, to=80, variable=self.automation_var, 
                                   orient=tk.HORIZONTAL, length=200)
        automation_scale.grid(row=0, column=1, padx=5)
        self.automation_label = ttk.Label(automation_frame, text="0%")
        self.automation_label.grid(row=0, column=2)
        automation_scale.configure(command=self.update_automation_label)
        
        self.automation_impact_label = ttk.Label(automation_frame, text="Impact: No automation", foreground='gray')
        self.automation_impact_label.grid(row=1, column=0, columnspan=3, sticky=tk.W)
        
        # Marketing
        marketing_frame = ttk.LabelFrame(decisions_frame, text="Marketing Investment", padding=5)
        marketing_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(marketing_frame, text="Marketing Spend (£):").grid(row=0, column=0, sticky=tk.W)
        self.marketing_var = tk.StringVar(value="0")
        marketing_entry = ttk.Entry(marketing_frame, textvariable=self.marketing_var, width=15)
        marketing_entry.grid(row=0, column=1, padx=5)
        marketing_entry.bind('<KeyRelease>', self.update_marketing_label)
        
        self.marketing_impact_label = ttk.Label(marketing_frame, text="Impact: No marketing spend", foreground='gray')
        self.marketing_impact_label.grid(row=1, column=0, columnspan=2, sticky=tk.W)
        
        # Scenarios
        self.create_scenario_selection_frame(parent)
        
        # Simulation Settings
        sim_frame = ttk.LabelFrame(parent, text="Simulation Settings", padding=10)
        sim_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(sim_frame, text="Monte Carlo Simulations:").grid(row=0, column=0, sticky=tk.W)
        self.sim_count_var = tk.IntVar(value=500)
        sim_combo = ttk.Combobox(sim_frame, textvariable=self.sim_count_var, 
                               values=[100, 250, 500, 1000, 2000], width=10, state='readonly')
        sim_combo.grid(row=0, column=1, padx=5)
        sim_combo.current(2)
        
        # Run button and progress
        run_frame = ttk.Frame(parent)
        run_frame.pack(fill=tk.X, padx=10, pady=20)
        
        self.run_button = ttk.Button(run_frame, text="Run Simulation", command=self.run_simulation)
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(run_frame, variable=self.progress_var, length=300)
        self.progress_bar.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        self.status_label = ttk.Label(run_frame, text="Ready to run simulation")
        self.status_label.pack(side=tk.RIGHT, padx=5)
    
    def create_growth_calculators(self, parent):
        # Main title
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(title_frame, text="Growth Rate Calculators", 
                 font=('Arial', 12, 'bold')).pack()
        ttk.Label(title_frame, text="Use your historical data to calculate growth rates", 
                 font=('Arial', 9), foreground='gray').pack()
        
        # Calculator 1: Historical Revenue Growth
        calc1_frame = ttk.LabelFrame(parent, text="Historical Revenue Growth Calculator", padding=10)
        calc1_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Instructions
        instruction_text = ("Enter revenue figures from consecutive years.\n"
                          "Example: 2022: £800,000 → 2023: £900,000 → 2024: £1,000,000")
        ttk.Label(calc1_frame, text=instruction_text, font=('Arial', 8), 
                 foreground='blue', wraplength=280).pack(anchor=tk.W, pady=(0, 10))
        
        # Revenue entry fields with dynamic rows
        self.revenue_entries_frame = ttk.Frame(calc1_frame)
        self.revenue_entries_frame.pack(fill=tk.X)
        
        self.revenue_entries = []
        self.year_entries = []
        
        # Initial 3 rows
        for i in range(3):
            self.add_revenue_row(i)
        
        # Add/Remove buttons
        button_frame = ttk.Frame(calc1_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(button_frame, text="Add Year", command=self.add_revenue_year).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Remove Year", command=self.remove_revenue_year).pack(side=tk.LEFT, padx=2)
        
        # Calculate button and result
        calc_button_frame = ttk.Frame(calc1_frame)
        calc_button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(calc_button_frame, text="Calculate Average Growth", 
                  command=self.calculate_historical_growth).pack(side=tk.LEFT)
        
        self.historical_result_label = ttk.Label(calc1_frame, text="Result: --", 
                                               foreground='green', font=('Arial', 10, 'bold'))
        self.historical_result_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Apply button
        ttk.Button(calc1_frame, text="Apply to Simulation", 
                  command=self.apply_historical_growth).pack(anchor=tk.W, pady=(5, 0))
        
        # Calculator 2: CAGR Calculator
        calc2_frame = ttk.LabelFrame(parent, text="Compound Annual Growth Rate (CAGR) Calculator", padding=10)
        calc2_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Instructions
        cagr_instruction = ("Enter starting value, ending value, and number of years\n"
                          "to calculate compound annual growth rate.")
        ttk.Label(calc2_frame, text=cagr_instruction, font=('Arial', 8), 
                 foreground='blue', wraplength=280).pack(anchor=tk.W, pady=(0, 10))
        
        # CAGR input fields
        cagr_input_frame = ttk.Frame(calc2_frame)
        cagr_input_frame.pack(fill=tk.X)
        
        ttk.Label(cagr_input_frame, text="Starting Value (£):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.cagr_start_var = tk.StringVar(value="")
        ttk.Entry(cagr_input_frame, textvariable=self.cagr_start_var, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(cagr_input_frame, text="Ending Value (£):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.cagr_end_var = tk.StringVar(value="")
        ttk.Entry(cagr_input_frame, textvariable=self.cagr_end_var, width=15).grid(row=1, column=1, padx=5)
        
        ttk.Label(cagr_input_frame, text="Number of Years:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.cagr_years_var = tk.IntVar(value=1)
        ttk.Spinbox(cagr_input_frame, from_=1, to=20, textvariable=self.cagr_years_var, width=13).grid(row=2, column=1, padx=5)
        
        # CAGR calculate button and result
        cagr_calc_frame = ttk.Frame(calc2_frame)
        cagr_calc_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(cagr_calc_frame, text="Calculate CAGR", 
                  command=self.calculate_cagr).pack(side=tk.LEFT)
        
        self.cagr_result_label = ttk.Label(calc2_frame, text="Result: --", 
                                         foreground='green', font=('Arial', 10, 'bold'))
        self.cagr_result_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Apply button
        ttk.Button(calc2_frame, text="Apply to Simulation", 
                  command=self.apply_cagr_growth).pack(anchor=tk.W, pady=(5, 0))
        
        # Example/Help section
        help_frame = ttk.LabelFrame(parent, text="Quick Help", padding=10)
        help_frame.pack(fill=tk.X, pady=(10, 0))
        
        help_text = ("Tips:\n"
                    "• Historical Calculator: Best for 3+ years of data\n"
                    "• CAGR Calculator: Perfect for start/end comparisons\n"
                    "• Industry average growth rates:\n"
                    "  - Mature industries: 2-5%\n"
                    "  - Growing sectors: 8-15%\n"
                    "  - Tech/startups: 20-50%")
        
        ttk.Label(help_frame, text=help_text, font=('Arial', 8), 
                 foreground='#333333', justify=tk.LEFT).pack(anchor=tk.W)
    
    def add_revenue_row(self, index):
        row_frame = ttk.Frame(self.revenue_entries_frame)
        row_frame.pack(fill=tk.X, pady=1)
        
        # Year entry
        year_var = tk.StringVar(value=str(2022 + index))
        year_entry = ttk.Entry(row_frame, textvariable=year_var, width=8)
        year_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Revenue entry
        revenue_var = tk.StringVar(value="")
        revenue_entry = ttk.Entry(row_frame, textvariable=revenue_var, width=15)
        revenue_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Labels
        ttk.Label(row_frame, text="Year", font=('Arial', 7)).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Label(row_frame, text="Revenue (£)", font=('Arial', 7)).pack(side=tk.RIGHT, padx=(10, 0))
        
        self.year_entries.append(year_var)
        self.revenue_entries.append(revenue_var)
    
    def add_revenue_year(self):
        if len(self.revenue_entries) < 10:  # Limit to 10 years
            self.add_revenue_row(len(self.revenue_entries))
    
    def remove_revenue_year(self):
        if len(self.revenue_entries) > 2:  # Keep minimum 2 years
            # Remove the last row
            last_frame = list(self.revenue_entries_frame.children.values())[-1]
            last_frame.destroy()
            self.year_entries.pop()
            self.revenue_entries.pop()
    
    def calculate_historical_growth(self):
        try:
            # Get revenue data
            revenues = []
            years = []
            
            for i, (year_var, revenue_var) in enumerate(zip(self.year_entries, self.revenue_entries)):
                year_str = year_var.get().strip()
                revenue_str = revenue_var.get().strip()
                
                if year_str and revenue_str:
                    year = int(year_str)
                    revenue = float(revenue_str.replace(',', ''))
                    years.append(year)
                    revenues.append(revenue)
            
            if len(revenues) < 2:
                messagebox.showwarning("Insufficient Data", "Please enter at least 2 years of revenue data.")
                return
            
            # Sort by year
            sorted_data = sorted(zip(years, revenues))
            years, revenues = zip(*sorted_data)
            
            # Calculate year-over-year growth rates
            growth_rates = []
            for i in range(1, len(revenues)):
                growth_rate = ((revenues[i] / revenues[i-1]) - 1) * 100
                growth_rates.append(growth_rate)
            
            # Calculate average growth rate
            avg_growth = sum(growth_rates) / len(growth_rates)
            
            # Show detailed results
            result_text = f"Average Growth Rate: {avg_growth:.2f}%\n"
            result_text += f"Based on {len(growth_rates)} year-over-year periods:\n"
            for i, rate in enumerate(growth_rates):
                result_text += f"  {years[i]} → {years[i+1]}: {rate:.1f}%\n"
            
            self.historical_result_label.config(text=f"Result: {avg_growth:.2f}% average growth")
            
            # Store for apply button
            self.calculated_historical_growth = avg_growth
            
            messagebox.showinfo("Historical Growth Calculation", result_text)
            
        except ValueError as e:
            messagebox.showerror("Input Error", "Please enter valid numbers for years and revenues.\nExample: Year: 2023, Revenue: 1000000")
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Error calculating growth rate: {str(e)}")
    
    def apply_historical_growth(self):
        if hasattr(self, 'calculated_historical_growth'):
            self.growth_var.set(self.calculated_historical_growth)
            self.growth_label.config(text=f"{self.calculated_historical_growth:.1f}%")
            messagebox.showinfo("Applied", f"Historical growth rate of {self.calculated_historical_growth:.2f}% applied to simulation.")
        else:
            messagebox.showwarning("No Calculation", "Please calculate historical growth rate first.")
    
    def calculate_cagr(self):
        try:
            start_value = float(self.cagr_start_var.get().replace(',', ''))
            end_value = float(self.cagr_end_var.get().replace(',', ''))
            years = self.cagr_years_var.get()
            
            if start_value <= 0 or end_value <= 0:
                messagebox.showerror("Invalid Input", "Values must be positive numbers.")
                return
            
            if years <= 0:
                messagebox.showerror("Invalid Input", "Number of years must be positive.")
                return
            
            # Calculate CAGR: (End Value / Start Value)^(1/years) - 1
            cagr = ((end_value / start_value) ** (1/years) - 1) * 100
            
            # Show detailed calculation
            total_growth = ((end_value / start_value) - 1) * 100
            result_text = (f"CAGR Calculation:\n"
                          f"Start Value: £{start_value:,.0f}\n"
                          f"End Value: £{end_value:,.0f}\n"
                          f"Time Period: {years} years\n"
                          f"Total Growth: {total_growth:.1f}%\n"
                          f"Compound Annual Growth Rate: {cagr:.2f}%")
            
            self.cagr_result_label.config(text=f"Result: {cagr:.2f}% CAGR")
            
            # Store for apply button
            self.calculated_cagr = cagr
            
            messagebox.showinfo("CAGR Calculation", result_text)
            
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numbers.\nExample: Start: 800000, End: 1200000, Years: 3")
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Error calculating CAGR: {str(e)}")
    
    def apply_cagr_growth(self):
        if hasattr(self, 'calculated_cagr'):
            self.growth_var.set(self.calculated_cagr)
            self.growth_label.config(text=f"{self.calculated_cagr:.1f}%")
            messagebox.showinfo("Applied", f"CAGR of {self.calculated_cagr:.2f}% applied to simulation.")
        else:
            messagebox.showwarning("No Calculation", "Please calculate CAGR first.")
    
    def create_scenario_selection_frame(self, parent):
        scenario_frame = ttk.LabelFrame(parent, text="Market Scenarios", padding=10)
        scenario_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(scenario_frame, text="Select Scenarios to Analyze:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        self.scenario_vars = {}
        for scenario in DEFAULT_SCENARIOS:
            var = tk.BooleanVar(value=True if scenario.name == "Normal Growth" else False)
            self.scenario_vars[scenario.name] = var
            
            frame = ttk.Frame(scenario_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Checkbutton(frame, text=scenario.name, variable=var).pack(side=tk.LEFT)
            ttk.Label(frame, text=f"- {scenario.description}", foreground='gray', font=('Arial', 8)).pack(side=tk.LEFT, padx=(10, 0))
        
        button_frame = ttk.Frame(scenario_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Select All", 
                  command=lambda: [var.set(True) for var in self.scenario_vars.values()]).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Select None", 
                  command=lambda: [var.set(False) for var in self.scenario_vars.values()]).pack(side=tk.LEFT)
    
    def create_results_tab(self):
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="Results & Charts")
        
        self.fig = Figure(figsize=(14, 10), facecolor='white')
        self.canvas = FigureCanvasTkAgg(self.fig, results_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar_frame = ttk.Frame(results_frame)
        toolbar_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(toolbar_frame, text="Save Charts", command=self.save_charts).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar_frame, text="Refresh", command=self.update_scenario_charts).pack(side=tk.LEFT, padx=5)
    
    def create_summary_tab(self):
        summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(summary_frame, text="Summary & Export")
        
        metrics_frame = ttk.LabelFrame(summary_frame, text="Key Metrics", padding=10)
        metrics_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.metrics_labels = {}
        metrics = [
            ("Revenue Growth", "revenue_growth"),
            ("Profit Growth", "profit_growth"), 
            ("Final Revenue", "final_revenue"),
            ("Final Profit", "final_profit"),
            ("Risk Level", "risk_level"),
            ("Profit Volatility", "profit_volatility")
        ]
        
        for i, (label, key) in enumerate(metrics):
            row, col = i // 3, (i % 3) * 2
            ttk.Label(metrics_frame, text=f"{label}:", font=('Arial', 10, 'bold')).grid(
                row=row, column=col, sticky=tk.W, padx=5, pady=2)
            self.metrics_labels[key] = ttk.Label(metrics_frame, text="--", foreground='blue')
            self.metrics_labels[key].grid(row=row, column=col+1, sticky=tk.W, padx=15, pady=2)
        
        summary_text_frame = ttk.LabelFrame(summary_frame, text="Executive Summary", padding=10)
        summary_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.summary_text = tk.Text(summary_text_frame, wrap=tk.WORD, height=15, font=('Arial', 10))
        summary_scrollbar = ttk.Scrollbar(summary_text_frame, command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scrollbar.set)
        
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        export_frame = ttk.Frame(summary_frame)
        export_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(export_frame, text="Export Summary CSV", command=self.export_summary_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Export Detailed CSV", command=self.export_detailed_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Export Report", command=self.export_text_summary).pack(side=tk.LEFT, padx=5)
    
    # Update methods
    def update_growth_label(self, value):
        self.growth_label.config(text=f"{float(value):.1f}%")
        
    def update_years_label(self, value):
        self.years_label.config(text=f"{int(float(value))} years")
    
    def update_staff_label_on_salary_change(self, event=None):
        # Trigger update when salary changes
        self.update_staff_label(self.staff_var.get())
        
    def update_staff_label(self, value):
        staff_count = int(float(value))
        self.staff_label.config(text=f"{staff_count} staff")
        if staff_count > 0:
            try:
                salary = float(self.salary_var.get())
                growth_impact = staff_count * 0.15  # 0.15% per employee
                cost_impact = staff_count * salary
                self.staff_impact_label.config(
                    text=f"Impact: +{growth_impact:.2f}% growth, +£{cost_impact:,} annual costs", foreground='blue')
            except ValueError:
                self.staff_impact_label.config(
                    text="Impact: Growth boost, cost depends on salary", foreground='orange')
        else:
            self.staff_impact_label.config(text="Impact: No change", foreground='gray')
    
    def update_expansion_label(self):
        if self.expansion_var.get():
            self.expansion_impact_label.config(text="Impact: +2% growth, +25% costs, +risk factor", foreground='blue')
        else:
            self.expansion_impact_label.config(text="Impact: No expansion", foreground='gray')
    
    def update_automation_label(self, value):
        automation_pct = float(value)
        self.automation_label.config(text=f"{automation_pct:.1f}%")
        if automation_pct > 0:
            try:
                base_costs = float(self.costs_var.get())
                cost_reduction = base_costs * (automation_pct / 100) * 0.003
                growth_boost = (automation_pct / 100) * 0.1
                self.automation_impact_label.config(
                    text=f"Impact: +{growth_boost:.2f}% growth, -£{cost_reduction:,.0f} annual costs", foreground='blue')
            except ValueError:
                self.automation_impact_label.config(text="Impact: Cost savings + productivity boost", foreground='blue')
        else:
            self.automation_impact_label.config(text="Impact: No automation", foreground='gray')
    
    def update_marketing_label(self, event=None):
        try:
            marketing_spend = float(self.marketing_var.get() or "0")
            if marketing_spend > 0:
                growth_boost = marketing_spend * 0.000002 * 100
                self.marketing_impact_label.config(
                    text=f"Impact: +{growth_boost:.3f}% growth, +£{marketing_spend:,.0f} annual costs", foreground='blue')
            else:
                self.marketing_impact_label.config(text="Impact: No marketing spend", foreground='gray')
        except ValueError:
            self.marketing_impact_label.config(text="Impact: Invalid marketing spend", foreground='red')
    
    def get_base_parameters(self) -> BusinessParameters:
        try:
            return BusinessParameters(
                base_revenue=float(self.revenue_var.get()),
                base_costs=float(self.costs_var.get()),
                num_employees=self.employees_var.get(),
                avg_employee_salary=float(self.salary_var.get()),
                baseline_growth_rate=self.growth_var.get() / 100,
                simulation_years=self.years_var.get()
            )
        except ValueError as e:
            messagebox.showerror("Input Error", f"Please check your input values: {str(e)}")
            return None
    
    def get_strategic_decisions(self) -> StrategicDecisions:
        try:
            return StrategicDecisions(
                staff_to_hire=self.staff_var.get(),
                expand_new_region=self.expansion_var.get(),
                automation_percentage=self.automation_var.get(),
                marketing_spend=float(self.marketing_var.get() or "0")
            )
        except ValueError as e:
            messagebox.showerror("Input Error", f"Please check your decision values: {str(e)}")
            return None
    
    def get_selected_scenarios(self) -> List[MarketScenario]:
        selected = []
        for scenario in DEFAULT_SCENARIOS:
            if self.scenario_vars[scenario.name].get():
                selected.append(scenario)
        
        if not selected:
            messagebox.showwarning("No Scenarios", "Please select at least one market scenario.")
            return None
        
        return selected
    
    def run_simulation(self):
        base_params = self.get_base_parameters()
        decisions = self.get_strategic_decisions()
        scenarios = self.get_selected_scenarios()
        
        if not all([base_params, decisions, scenarios]):
            return
        
        self.current_base_params = base_params
        self.current_decisions = decisions
        
        # Update simulator with selected number of simulations
        self.simulator.num_simulations = self.sim_count_var.get()
        
        # Disable the run button during simulation
        self.run_button.config(state='disabled', text="Running...")
        
        def progress_callback(message, progress=None):
            if progress is not None:
                self.progress_var.set(progress)
            self.status_label.config(text=str(message))
            self.root.update_idletasks()
        
        def run_in_thread():
            try:
                # Calculate impacts first
                impact_calc = DecisionImpactCalculator()
                self.current_impacts = impact_calc.calculate_impacts(decisions, base_params)
                
                # Run scenario analysis
                self.current_results = self.simulator.run_scenario_analysis(
                    base_params, decisions, scenarios, progress_callback
                )
                
                # Update GUI in main thread
                self.root.after(0, self.simulation_complete)
                
            except Exception as e:
                messagebox.showerror("Simulation Error", f"An error occurred during simulation: {str(e)}")
                self.root.after(0, self.simulation_failed)
        
        # Start simulation in background thread
        thread = threading.Thread(target=run_in_thread)
        thread.daemon = True
        thread.start()
    
    def simulation_complete(self):
        self.run_button.config(state='normal', text="Run Simulation")
        self.progress_var.set(100)
        self.status_label.config(text="Simulation complete!")
        
        # Update all tabs with results
        self.update_scenario_charts()
        self.update_summary_metrics()
        self.update_executive_summary()
        
        # Switch to results tab
        self.notebook.select(1)
        
        messagebox.showinfo("Success", "Simulation completed successfully!")
    
    def simulation_failed(self):
        self.run_button.config(state='normal', text="Run Simulation")
        self.progress_var.set(0)
        self.status_label.config(text="Simulation failed")
    
    def update_scenario_charts(self):
        if not self.current_results:
            return
        
        self.fig.clear()
        
        # Create subplots
        gs = self.fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        ax1 = self.fig.add_subplot(gs[0, 0])
        ax2 = self.fig.add_subplot(gs[0, 1])
        ax3 = self.fig.add_subplot(gs[1, 0])
        ax4 = self.fig.add_subplot(gs[1, 1])
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        # Revenue growth comparison
        for i, (scenario_name, results) in enumerate(self.current_results.items()):
            # Calculate mean revenue by year
            year_groups = results.groupby('Year').agg({'Revenue': ['mean']})
            years = list(year_groups.keys())
            mean_revenues = [year_groups[year]['Revenue_mean'] for year in years]
            
            ax1.plot(years, mean_revenues, marker='o', label=scenario_name, 
                    color=colors[i % len(colors)], linewidth=2)
        
        ax1.set_title('Revenue Growth by Scenario', fontweight='bold')
        ax1.set_xlabel('Year')
        ax1.set_ylabel('Revenue (£)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
        
        # Profit comparison
        for i, (scenario_name, results) in enumerate(self.current_results.items()):
            year_groups = results.groupby('Year').agg({'Net_Profit': ['mean']})
            years = list(year_groups.keys())
            mean_profits = [year_groups[year]['Net_Profit_mean'] for year in years]
            
            ax2.plot(years, mean_profits, marker='s', label=scenario_name, 
                    color=colors[i % len(colors)], linewidth=2)
        
        ax2.set_title('Net Profit by Scenario', fontweight='bold')
        ax2.set_xlabel('Year')
        ax2.set_ylabel('Net Profit (£)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
        
        # Risk analysis - profit volatility
        volatilities = []
        scenario_names = []
        for scenario_name, results in self.current_results.items():
            final_year_profits = [row['Net_Profit'] for row in results.data 
                                if row['Year'] == self.current_base_params.simulation_years]
            volatility = np.std(final_year_profits) / np.mean(final_year_profits) * 100
            volatilities.append(volatility)
            scenario_names.append(scenario_name)
        
        bars = ax3.bar(scenario_names, volatilities, color=colors[:len(scenario_names)])
        ax3.set_title('Profit Volatility by Scenario', fontweight='bold')
        ax3.set_xlabel('Scenario')
        ax3.set_ylabel('Coefficient of Variation (%)')
        ax3.tick_params(axis='x', rotation=45)
        ax3.grid(True, alpha=0.3)
        
        # Probability distributions for final year profit
        final_year = self.current_base_params.simulation_years
        for i, (scenario_name, results) in enumerate(self.current_results.items()):
            final_profits = [row['Net_Profit'] for row in results.data if row['Year'] == final_year]
            ax4.hist(final_profits, bins=30, alpha=0.6, label=scenario_name, 
                    color=colors[i % len(colors)], density=True)
        
        ax4.set_title(f'Final Year Profit Distribution', fontweight='bold')
        ax4.set_xlabel('Net Profit (£)')
        ax4.set_ylabel('Probability Density')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        ax4.ticklabel_format(style='scientific', axis='x', scilimits=(0,0))
        
        self.canvas.draw()
    
    def update_summary_metrics(self):
        if not self.current_results or not self.current_base_params:
            return
        
        # Calculate key metrics from Normal Growth scenario (or first available)
        scenario_name = "Normal Growth" if "Normal Growth" in self.current_results else list(self.current_results.keys())[0]
        results = self.current_results[scenario_name]
        
        # Initial values
        initial_revenue = self.current_base_params.base_revenue
        initial_profit = initial_revenue - self.current_base_params.base_costs
        final_year = self.current_base_params.simulation_years
        
        # Final year values (mean)
        final_revenues = [row['Revenue'] for row in results.data if row['Year'] == final_year]
        final_profits = [row['Net_Profit'] for row in results.data if row['Year'] == final_year]
        
        mean_final_revenue = np.mean(final_revenues)
        mean_final_profit = np.mean(final_profits)
        
        # Growth calculations
        revenue_growth = ((mean_final_revenue / initial_revenue) ** (1/final_year) - 1) * 100
        profit_growth = ((mean_final_profit / initial_profit) ** (1/final_year) - 1) * 100 if initial_profit > 0 else 0
        
        # Risk metrics
        profit_volatility = np.std(final_profits) / np.mean(final_profits) * 100 if np.mean(final_profits) > 0 else 0
        risk_level = "Low" if profit_volatility < 10 else "Medium" if profit_volatility < 25 else "High"
        
        # Update labels
        self.metrics_labels["revenue_growth"].config(text=f"{revenue_growth:.1f}% p.a.")
        self.metrics_labels["profit_growth"].config(text=f"{profit_growth:.1f}% p.a.")
        self.metrics_labels["final_revenue"].config(text=f"£{mean_final_revenue:,.0f}")
        self.metrics_labels["final_profit"].config(text=f"£{mean_final_profit:,.0f}")
        self.metrics_labels["risk_level"].config(text=risk_level)
        self.metrics_labels["profit_volatility"].config(text=f"{profit_volatility:.1f}%")
    
    def update_executive_summary(self):
        if not self.current_results or not self.current_base_params or not self.current_impacts:
            return
        
        summary = []
        summary.append("BUSINESS SIMULATION EXECUTIVE SUMMARY")
        summary.append("=" * 50)
        summary.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append("")
        
        # Base scenario
        summary.append("BASE PARAMETERS:")
        summary.append(f"  • Initial Revenue: £{self.current_base_params.base_revenue:,.0f}")
        summary.append(f"  • Initial Costs: £{self.current_base_params.base_costs:,.0f}")
        summary.append(f"  • Initial Profit: £{self.current_base_params.base_revenue - self.current_base_params.base_costs:,.0f}")
        summary.append(f"  • Employees: {self.current_base_params.num_employees:,}")
        summary.append(f"  • Average Employee Salary: £{self.current_base_params.avg_employee_salary:,.0f}")
        summary.append(f"  • Baseline Growth: {self.current_base_params.baseline_growth_rate*100:.1f}%")
        summary.append(f"  • Simulation Period: {self.current_base_params.simulation_years} years")
        summary.append("")
        
        # Strategic decisions impact
        summary.append("STRATEGIC DECISIONS IMPACT:")
        impacts = self.current_impacts
        if impacts['growth_rate_adjustment'] != 0:
            summary.append(f"  • Growth Rate Adjustment: +{impacts['growth_rate_adjustment']*100:.2f}%")
        if impacts['cost_adjustment'] != 0:
            summary.append(f"  • Annual Cost Adjustment: £{impacts['cost_adjustment']:,.0f}")
        if impacts['risk_factor'] != 0:
            summary.append(f"  • Additional Risk Factor: {impacts['risk_factor']*100:.1f}%")
        
        # Breakdown by decision type
        breakdown = impacts['breakdown']
        for decision_type, impact in breakdown.items():
            if any(v != 0 for v in impact.values()):
                if decision_type == 'hiring' and impact.get('cost', 0) != 0:
                    summary.append(f"    - {decision_type.title()}: Growth +{impact.get('growth', 0)*100:.3f}%, Cost £{impact.get('cost', 0):,.0f} (@ £{self.current_base_params.avg_employee_salary:,.0f}/employee)")
                else:
                    summary.append(f"    - {decision_type.title()}: Growth +{impact.get('growth', 0)*100:.3f}%, Cost £{impact.get('cost', 0):,.0f}")
        summary.append("")
        
        # Scenario results
        summary.append("SCENARIO ANALYSIS RESULTS:")
        for scenario_name, results in self.current_results.items():
            final_year = self.current_base_params.simulation_years
            final_revenues = [row['Revenue'] for row in results.data if row['Year'] == final_year]
            final_profits = [row['Net_Profit'] for row in results.data if row['Year'] == final_year]
            
            mean_revenue = np.mean(final_revenues)
            mean_profit = np.mean(final_profits)
            profit_volatility = np.std(final_profits) / mean_profit * 100 if mean_profit > 0 else 0
            
            # Calculate CAGR
            initial_revenue = self.current_base_params.base_revenue
            revenue_cagr = ((mean_revenue / initial_revenue) ** (1/final_year) - 1) * 100
            
            summary.append(f"  {scenario_name}:")
            summary.append(f"    • Final Revenue: £{mean_revenue:,.0f} (CAGR: {revenue_cagr:.1f}%)")
            summary.append(f"    • Final Profit: £{mean_profit:,.0f}")
            summary.append(f"    • Profit Volatility: {profit_volatility:.1f}%")
            
            # Risk assessment
            if profit_volatility < 10:
                risk_desc = "Low risk"
            elif profit_volatility < 25:
                risk_desc = "Medium risk"
            else:
                risk_desc = "High risk"
            summary.append(f"    • Risk Level: {risk_desc}")
            summary.append("")
        
        # Recommendations
        summary.append("RECOMMENDATIONS:")
        
        # Find best and worst scenarios
        scenario_profits = {}
        for scenario_name, results in self.current_results.items():
            final_profits = [row['Net_Profit'] for row in results.data 
                           if row['Year'] == self.current_base_params.simulation_years]
            scenario_profits[scenario_name] = np.mean(final_profits)
        
        best_scenario = max(scenario_profits, key=scenario_profits.get)
        worst_scenario = min(scenario_profits, key=scenario_profits.get)
        
        summary.append(f"  • Best case scenario: {best_scenario}")
        summary.append(f"    Expected final profit: £{scenario_profits[best_scenario]:,.0f}")
        summary.append(f"  • Worst case scenario: {worst_scenario}")
        summary.append(f"    Expected final profit: £{scenario_profits[worst_scenario]:,.0f}")
        summary.append("")
        
        # Decision-based recommendations
        if self.current_decisions.staff_to_hire > 0:
            summary.append(f"  • Staff hiring shows positive growth impact - monitor productivity gains")
            summary.append(f"    (Hiring {self.current_decisions.staff_to_hire} employees at £{self.current_base_params.avg_employee_salary:,.0f} each)")
        if self.current_decisions.expand_new_region:
            summary.append("  • Regional expansion increases both growth potential and risk - ensure market research")
        if self.current_decisions.automation_percentage > 0:
            summary.append("  • Automation provides cost savings - plan for employee transition")
        if self.current_decisions.marketing_spend > 0:
            summary.append("  • Marketing investment shows growth potential - track ROI carefully")
        
        summary.append("")
        summary.append("RISK CONSIDERATIONS:")
        if impacts['risk_factor'] > 0.05:
            summary.append("  • High risk strategy - ensure adequate cash reserves")
        if any(scenario_profits[s] < 0 for s in scenario_profits):
            summary.append("  • Some scenarios show potential losses - consider contingency planning")
        
        summary.append("")
        summary.append(f"Simulation completed with {self.simulator.num_simulations} Monte Carlo iterations per scenario.")
        
        # Update text widget
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, "\n".join(summary))
    
    # Export methods
    def export_summary_csv(self):
        if not self.current_results:
            messagebox.showwarning("No Data", "Please run a simulation first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Summary CSV"
        )
        
        if filename:
            try:
                summary_data = []
                for scenario_name, results in self.current_results.items():
                    final_year = self.current_base_params.simulation_years
                    year_groups = results.groupby('Year').agg({
                        'Revenue': ['mean', 'std', 'min', 'max'],
                        'Net_Profit': ['mean', 'std', 'min', 'max'],
                        'Profit_Margin': ['mean', 'std']
                    })
                    
                    for year in year_groups.keys():
                        summary_data.append({
                            'Scenario': scenario_name,
                            'Year': year,
                            'Revenue_Mean': year_groups[year]['Revenue_mean'],
                            'Revenue_Std': year_groups[year]['Revenue_std'],
                            'Revenue_Min': year_groups[year]['Revenue_min'],
                            'Revenue_Max': year_groups[year]['Revenue_max'],
                            'Profit_Mean': year_groups[year]['Net_Profit_mean'],
                            'Profit_Std': year_groups[year]['Net_Profit_std'],
                            'Profit_Min': year_groups[year]['Net_Profit_min'],
                            'Profit_Max': year_groups[year]['Net_Profit_max'],
                            'Margin_Mean': year_groups[year]['Profit_Margin_mean'],
                            'Margin_Std': year_groups[year]['Profit_Margin_std']
                        })
                
                df = SimpleDataFrame(summary_data)
                df.to_csv(filename)
                messagebox.showinfo("Success", f"Summary exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export summary: {str(e)}")
    
    def export_detailed_csv(self):
        if not self.current_results:
            messagebox.showwarning("No Data", "Please run a simulation first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Detailed CSV"
        )
        
        if filename:
            try:
                all_data = []
                for scenario_name, results in self.current_results.items():
                    all_data.extend(results.data)
                
                df = SimpleDataFrame(all_data)
                df.to_csv(filename)
                messagebox.showinfo("Success", f"Detailed data exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export detailed data: {str(e)}")
    
    def export_text_summary(self):
        if not self.current_results:
            messagebox.showwarning("No Data", "Please run a simulation first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Text Summary"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.summary_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Text summary exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export text summary: {str(e)}")
    
    def save_charts(self):
        if not self.current_results:
            messagebox.showwarning("No Data", "Please run a simulation first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Save Charts"
        )
        
        if filename:
            try:
                self.fig.savefig(filename, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Success", f"Charts saved to {filename}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save charts: {str(e)}")
    
    def run(self):
        self.root.mainloop()

# Main execution
if __name__ == "__main__":
    try:
        app = BusinessSimulatorGUI()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()
