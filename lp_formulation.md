# Sets

- $A$: Set of areas {A1, A2, A3}
- $C_a$: Set of cities in area A

# Indices

- $a:$ area 1,2,3
- $c_a:$ city in city name list for given area [Warshava, …]
- $i,j \in C_1 UC_2UC_3$

# Objective

- $Min[z]=\sum_i \sum_j d_{ij}*x_{ij}$

# Variables

- $x_{ij}$: binary, is there a cable from city i to city j
- $w_i$: is the city i connected to the line or not (binary)

# Parameters

- $d_{ij}$: distance from city i to city j

# Constraints

## Is city W connected

- $w_i=\sum_j x_{ji}, \qquad w_i=\sum_j x_{ij} \qquad \forall i \notin \{\text{Warszawa}, \text{Jelenia Góra}\}$
    - also handles balance, as #cablesIn=#cablesOut

## Area constraints

- Area 1: Warsaw → Radom, through two other area-1 cities
    - the line must pass through Warsaw, Radom and 2 other cities in area1 1
    - $w_{warsaw}=1$
    - $w_{Radom}=1$
    - $\sum_{c \in C_1}w_c=4$: the sum of passed through cities in area 1 must be at least 4
- Area 2: Kielce → Gliwice, through three other area-2 cities
    - the line must pass through Kielce, Gliwise and exactly three more cities in area 2
    - $w_{kielce}=1$
    - $w_{Gliwise}=1$
    - $\sum_{c \in C_2}w_c=5$: the sum of passed through cities in area 2 must be exactly 5
- Area 3: Opole → Jelenia Góra, through three other area-3 cities
    - the line must pass through Opole, Jelenia Góra and exactly three more cities in area 3
    - $w_{Opole}=1$
    - $w_{Jelenia Góra}=1$
    - $\sum_{c \in C_3}w_c=5$: the sum of passed through cities in area 3 must be exactly 5

### City coverage

- at least one of Konin and Kalisz are on the line
    - There must be at least one cable in either Konin of Kalisz
    - $w_{\text{Konin}} + w_{\text{Kalisz}} \ge 1$
- at least one of Poznań, Zielona Góra and Leszno are on the line
    - $w_{\text{Poznań}} + w_{\text{Zielona Góra}} + w_{\text{Leszno}} \ge 1$
- at most one of Bytom, Sosnowiec and Katowice are on the line
    - $w_{\text{Bytom}} + w_{\text{Sosnowiec}} + w_{\text{Katowice}} \le 1$
- at most one of Wodzisław Śląski and Jastrzębie-Zdrój are on the line
    - $w_{\text{Wodzisław}} + w_{\text{Jastrzębie}} \le 1$

## No self loops

- $x_{ij}=0 \forall i=j$

## Cables only within the same area

- $x_{ij}=0|i\in C_a, j \notin C_a$, except for Radom-Kielce, gwilice-opole

## Must use existing cables

- $x_{radom, kielce}=1$
- $x_{gwilice,opole}=1$

## Must start in warsawa, end in Jelenia Gora

- $\sum_jx_{warshawa,j}=1$
    - $\sum_jx_{j, warshawa,}=0$
- $\sum_i x_{i, Jelemnia Gora}=1$
    - $\sum_i x_{Jelemnia Gora,i}=0$

## Not two way cable

- $x_{ij}+x_{ji}≤1$

## No cycles

- we have to make a line, not a cycle
    - $\sum_{i\in S}\sum_{j\in S} x_{ij} \;\le\; |S|-1 \qquad \forall\, a\in A,\ S\subseteq C_a,\ |S|\ge 2$

## No cycles

- we have to make one line, not a line + separate loops on the side (subtours)
- subtour elimination: a set of cities $S$ can have at most $|S|-1$ cables inside it
    - $\sum_{i\in S}\sum_{j\in S,\, j\neq i} x_{ij} \le |S|-1 \qquad \forall\, a\in A,\ S\subseteq C_a,\ |S|\ge 2$
    - loop through k cities = k cables → not allowed
    - line through k cities = k-1 cables → ok

### Binary, Non negativity

- All cables either exist or dont.
    - 0 indicates no cable, while 1 indicates there is a cable
    - $x_{ij} \in \{0,1\}$
- A city is either connected or not
    - $w_i \in \{0,1\}$