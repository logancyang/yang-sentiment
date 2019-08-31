import json
import us


# Map **user** location to US state abbr
def map_raw_to_states(counts_raw_list, top_n=15):
    us_states_dict = us.states.mapping('abbr', 'name')
    # original location text : State short name
    state_raw_map = {key: [] for key, val in us_states_dict.items()}
    for loc, count in counts_raw_list:
        state_abbr = get_state_abbr(loc)
        if state_abbr:
            state_raw_map[state_abbr].append(loc)
    state_hist = [(key, len(val)) for key, val in state_raw_map.items()]
    state_hist_sorted = sorted(state_hist, key=lambda tup: tup[1], reverse=True)[:top_n]
    return state_hist_sorted, state_raw_map


def get_state_abbr(loc):
    if not loc:
        return
    us_states_dict = us.states.mapping('name', 'abbr')
    # If explicit state name or abbr exists, return
    for name, abbr in us_states_dict.items():
        if abbr in loc or name in loc:
            return abbr
    # If only city name exists, map city to state abbr
    with open('./locdata/cities.json', 'r') as f:
        cities_json = json.load(f)
    uscity_dict = {item['city']: item for item in cities_json}
    for city, city_data in uscity_dict.items():
        if loc.lower().strip() in city.lower().split(' '):
            state_name = city_data['state']
            abbr = us_states_dict.get(state_name)
            return abbr
    return
