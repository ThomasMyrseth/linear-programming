# Sets

- $City=\{\text{set of cities, not on mainline}\}$
- $SwitchingStation=\{Warsawa, Kiele, Opole\}$

# Parameters

- $d_{ij}$: Euclidian distance from city i to city j
- $cost=1000€/Coordinate/TB/s$: cost of cable per coordinate unit per TB/s
- $maxThroughput=200TB/s$
- $switchStation=400TB/s$
- $NumberOfSwitchingStations=\{2,3,1\}$
- $Demand=\{\text{demand per city}\}$

# Indices

- $c$: city c
- $s_c$: switching station city c connected to

# Variables

- $x_{ij}$: capacity used between city i and j

# Objective

- $Min[z]=\sum_i\sum_j x_{ij}*cost*d_{ij}$

# Constraints

- max theoretical capacity per x_ij 200TB/s
    - $\forall_{ij} x_{ij}≤maxTroughput$
- max capacity considering loss over distance
    - x≤ 2πmin(35, 70− d)
    - $\forall_{ij}x_{ij}≤2*\pi*min[35, 70 - d_{ij}]$
- lodz: max 40% of capacity per cable
    - $x_{\text{Łódź},j} \le 0.4 \sum_k x_{\text{Łódź},k} \quad \forall j$
- all cities must be directly connected to a switching station
    - $\sum_{switchingStation}\sum_i x_{i,switcingStation}=\sum_idemand_i$
- capacity constraint at switching station
    - $\forall_{switchingStation}:\sum_i x_{i,switcingStation}≤switchStation*NumberOfSwitchStation_{switchStation}$
- meet city demand requirements (RHS)
    - $~~\forall_i:\sum_{switchingStation} x_{i,switchinsStation}=demand_i~~$
- no self loops for one city only
    - $\forall _i: x_{ii}=0$
- ~~balance requirement, sum into city equals out (except switchig station)~~
    - $\forall_i:\sum_j x_{ij}=\sum_j x_{ji}+demand_i$ sum out equal sum in + demand out
- ~~no loops (this will never have this as it will always be cheaper to not have a loop)~~

## Non negative

- $x_{ij}≥0$