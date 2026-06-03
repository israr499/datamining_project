# ============================================
# create_test_data.py
# Generate CSV files for ElectroGuard testing
# ============================================

import pandas as pd
import numpy as np
import os

def generate_household_data(household_id, pattern='normal'):
    """
    Generate 96 consumption values for a single household (24 hours × 15-min intervals)
    
    Patterns:
    - 'normal': Regular household consumption (morning/evening peaks)
    - 'theft_peak_clipping': Meter tampering - caps peak readings
    - 'theft_night_zeroing': Illegal disconnection at night
    - 'theft_reduction': Meter bypass - reduces all readings
    - 'theft_spike': Illegal connection - sudden high usage
    """
    consumption = []
    
    for hour in range(24):
        for minute in [0, 15, 30, 45]:
            
            if pattern == 'normal':
                # Normal household pattern
                if 6 <= hour <= 8:      # Morning peak (6-9 AM)
                    val = np.random.uniform(0.8, 1.5)
                elif 17 <= hour <= 20:   # Evening peak (5-8 PM)
                    val = np.random.uniform(1.0, 2.0)
                elif 23 <= hour or hour <= 5:  # Night time (11 PM - 5 AM)
                    val = np.random.uniform(0, 0.3)
                else:                     # Daytime off-peak
                    val = np.random.uniform(0.3, 0.7)
            
            elif pattern == 'theft_peak_clipping':
                # Peak clipping - meter tampering (readings capped)
                if 6 <= hour <= 8:
                    val = np.random.uniform(0.5, 0.9)  # Capped!
                elif 17 <= hour <= 20:
                    val = np.random.uniform(0.6, 1.0)  # Capped!
                elif 23 <= hour or hour <= 5:
                    val = np.random.uniform(0, 0.2)
                else:
                    val = np.random.uniform(0.2, 0.5)
            
            elif pattern == 'theft_night_zeroing':
                # Night zeroing - meter tampering at night
                if 23 <= hour or hour <= 5:
                    val = 0  # Completely zero at night!
                elif 6 <= hour <= 8:
                    val = np.random.uniform(0.7, 1.3)
                elif 17 <= hour <= 20:
                    val = np.random.uniform(0.9, 1.8)
                else:
                    val = np.random.uniform(0.3, 0.6)
            
            elif pattern == 'theft_reduction':
                # Overall reduction - meter bypass (40% reduction)
                if 6 <= hour <= 8:
                    val = np.random.uniform(0.5, 0.9)   # Reduced
                elif 17 <= hour <= 20:
                    val = np.random.uniform(0.6, 1.2)   # Reduced
                elif 23 <= hour or hour <= 5:
                    val = np.random.uniform(0, 0.2)
                else:
                    val = np.random.uniform(0.2, 0.4)   # Reduced
            
            elif pattern == 'theft_spike':
                # Sudden spikes - illegal connection / crypto mining
                if 6 <= hour <= 8:
                    val = np.random.uniform(0.7, 1.3)
                elif 17 <= hour <= 20:
                    val = np.random.uniform(0.9, 1.8)
                elif 23 <= hour or hour <= 5:
                    # Random spikes at night (suspicious!)
                    val = np.random.uniform(0, 2.5)
                else:
                    val = np.random.uniform(0.3, 0.7)
            
            consumption.append(round(val, 3))
    
    return consumption


def create_test_csv():
    """Create all test CSV files"""
    
    print("="*60)
    print("📊 Creating Test CSV Files for ElectroGuard")
    print("="*60)
    
    # Create data folder if it doesn't exist
    os.makedirs('data/test_csv', exist_ok=True)
    
    # ============================================
    # FILE 1: Normal Households Only
    # ============================================
    print("\n📝 Creating normal_households.csv...")
    normal_data = []
    for i in range(1, 11):  # 10 normal households
        consumption = generate_household_data(f'NORMAL_{i:03d}', 'normal')
        row = {'household_id': f'NORMAL_{i:03d}'}
        for j, val in enumerate(consumption):
            row[f'interval_{j+1}'] = val
        normal_data.append(row)
    
    df_normal = pd.DataFrame(normal_data)
    df_normal.to_csv('data/test_csv/normal_households.csv', index=False)
    print(f"   ✅ Created: 10 normal households")
    
    # ============================================
    # FILE 2: Theft Households Only
    # ============================================
    print("\n📝 Creating theft_households.csv...")
    theft_patterns = ['theft_peak_clipping', 'theft_night_zeroing', 'theft_reduction', 'theft_spike']
    theft_data = []
    
    for i, pattern in enumerate(theft_patterns):
        for j in range(3):  # 3 households per pattern = 12 total
            household_id = f'THEFT_{pattern.replace("theft_", "").upper()[:3]}_{j+1:02d}'
            consumption = generate_household_data(household_id, pattern)
            row = {'household_id': household_id}
            for idx, val in enumerate(consumption):
                row[f'interval_{idx+1}'] = val
            theft_data.append(row)
    
    df_theft = pd.DataFrame(theft_data)
    df_theft.to_csv('data/test_csv/theft_households.csv', index=False)
    print(f"   ✅ Created: 12 theft households (4 patterns × 3 each)")
    
    # ============================================
    # FILE 3: Mixed Dataset (Normal + Theft)
    # ============================================
    print("\n📝 Creating mixed_test.csv...")
    mixed_data = []
    
    # Add 10 normal households
    for i in range(1, 11):
        consumption = generate_household_data(f'MIXED_NORMAL_{i:03d}', 'normal')
        row = {'household_id': f'MIXED_NORMAL_{i:03d}'}
        for j, val in enumerate(consumption):
            row[f'interval_{j+1}'] = val
        mixed_data.append(row)
    
    # Add 10 theft households
    for i in range(1, 11):
        # Alternate between theft patterns
        pattern = theft_patterns[i % len(theft_patterns)]
        consumption = generate_household_data(f'MIXED_THEFT_{i:03d}', pattern)
        row = {'household_id': f'MIXED_THEFT_{i:03d}'}
        for j, val in enumerate(consumption):
            row[f'interval_{j+1}'] = val
        mixed_data.append(row)
    
    df_mixed = pd.DataFrame(mixed_data)
    df_mixed.to_csv('data/test_csv/mixed_test.csv', index=False)
    print(f"   ✅ Created: 20 mixed households (10 normal + 10 theft)")
    
    # ============================================
    # FILE 4: Single Household Demo
    # ============================================
    print("\n📝 Creating single_demo.csv...")
    demo_patterns = ['normal', 'theft_peak_clipping', 'theft_night_zeroing', 'theft_reduction', 'theft_spike']
    demo_data = []
    
    for pattern in demo_patterns:
        consumption = generate_household_data(f'DEMO_{pattern.upper()[:8]}', pattern)
        row = {'household_id': f'DEMO_{pattern.upper()[:8]}'}
        for j, val in enumerate(consumption):
            row[f'interval_{j+1}'] = val
        demo_data.append(row)
    
    df_demo = pd.DataFrame(demo_data)
    df_demo.to_csv('data/test_csv/single_demo.csv', index=False)
    print(f"   ✅ Created: 5 demo households (1 normal + 4 theft patterns)")
    
    # ============================================
    # Summary
    # ============================================
    print("\n" + "="*60)
    print("✅ ALL CSV FILES CREATED SUCCESSFULLY!")
    print("="*60)
    print("\n📁 Files saved in: electroguard/data/test_csv/")
    print("\n📋 File List:")
    print("   1. normal_households.csv  - 10 normal households")
    print("   2. theft_households.csv   - 12 theft households")
    print("   3. mixed_test.csv         - 20 mixed (normal + theft)")
    print("   4. single_demo.csv        - 5 demo patterns")
    print("\n🚀 How to use:")
    print("   1. Run: python run.py")
    print("   2. Go to: Predict & Detect page")
    print("   3. Click 'Upload CSV' tab")
    print("   4. Upload any of these files")
    print("   5. Click 'Predict All Households'")
    print("="*60)
    
    # Show preview
    print("\n📊 Preview of mixed_test.csv (first 3 households):")
    print(df_mixed.head(3).to_string())
    
    return True


def create_simple_csv_manually():
    """
    Create a VERY SIMPLE CSV file manually (no pandas required)
    Use if pandas is not available
    """
    
    os.makedirs('data/test_csv', exist_ok=True)
    
    # Simple CSV content
    csv_content = '''household_id,interval_1,interval_2,interval_3,interval_4,interval_5,interval_6,interval_7,interval_8,interval_9,interval_10,interval_11,interval_12,interval_13,interval_14,interval_15,interval_16,interval_17,interval_18,interval_19,interval_20,interval_21,interval_22,interval_23,interval_24,interval_25,interval_26,interval_27,interval_28,interval_29,interval_30,interval_31,interval_32,interval_33,interval_34,interval_35,interval_36,interval_37,interval_38,interval_39,interval_40,interval_41,interval_42,interval_43,interval_44,interval_45,interval_46,interval_47,interval_48,interval_49,interval_50,interval_51,interval_52,interval_53,interval_54,interval_55,interval_56,interval_57,interval_58,interval_59,interval_60,interval_61,interval_62,interval_63,interval_64,interval_65,interval_66,interval_67,interval_68,interval_69,interval_70,interval_71,interval_72,interval_73,interval_74,interval_75,interval_76,interval_77,interval_78,interval_79,interval_80,interval_81,interval_82,interval_83,interval_84,interval_85,interval_86,interval_87,interval_88,interval_89,interval_90,interval_91,interval_92,interval_93,interval_94,interval_95,interval_96
NORMAL,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.3,0.3,0.3,0.3,0.4,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.2,1.2,1.1,1.0,0.9,0.8,0.7,0.6,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.3,1.4,1.5,1.5,1.5,1.4,1.3,1.2,1.1,1.0,0.9,0.8,0.7,0.6,0.5,0.4,0.3,0.3,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2
THEFT,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0'''
    
    with open('data/test_csv/simple_test.csv', 'w') as f:
        f.write(csv_content)
    
    print("✅ Created simple_test.csv with 2 households")
    return True


# ============================================
# RUN THE SCRIPT
# ============================================
if __name__ == '__main__':
    try:
        # Try with pandas first
        create_test_csv()
    except ImportError:
        print("⚠️ Pandas not installed, creating simple CSV instead...")
        create_simple_csv_manually()