# coding: utf-8
idx_approach_end = idx_landing_start  = 3975
m1 = df.loc[idx_landing_start:, 'radio_altitude_derived'] >= 500
idx_landing_end = m1.idxmax()
landing_data_slice = df.iloc[idx_landing_start: idx_landing_end+1]
temp_mask = (landing_data_slice['eng_1_rpm'] > 2200) & (landing_data_slice['groundspeed'] > 25) & (landing_data_slice['indicated_airspeed'] > 0)
idx_takeoff_start = temp_mask.idxmax()
temp = landing_data_slice.loc[idx_takeoff_start:]
speeds = temp['indicated_airspeed']
x = speeds.diff()
m = x < 0
temp.loc[:, 'speed_diff'] = x
temp[['indicated_airspeed', 'radio_altitude_derived', 'speed_diff']]
temp.loc[m, ['indicated_airspeed', 'radio_altitude_derived', 'speed_diff']]
np.average(temp.loc[m, 'radio_altitude_derived'])
np.average(temp.loc[m, 'speed_diff'])
