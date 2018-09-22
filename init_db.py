import json
import psycopg2
import requests
import os

def swapi_list_resource(url):
    next_url = url
    while next_url:
        print(next_url)
        res = requests.get(next_url)
        res.raise_for_status()
        json = res.json()

        for item in json.get('results', []):
            yield item

        next_url = json.get('next', None)

def swapi_list_resource_cached(url):
    cachename = os.path.join('.swapicache', url.replace(':', '-').replace('/', '-'))
    if os.path.isfile(cachename):
        with open(cachename, 'r') as f:
            return json.load(f)

    items = [x for x in swapi_list_resource(url)]
    with open(cachename, 'w') as f:
        json.dump(items, f)
    return items

data = {
    'people': swapi_list_resource_cached('https://swapi.co/api/people'),
    'planets': swapi_list_resource_cached('https://swapi.co/api/planets'),
}

dbconn = psycopg2.connect(dbname='starwarsdb',
                          user='prisma',
                          password='prisma123',
                          host='localhost',
                          port=5432)
dbcur = dbconn.cursor()

def sql(stmt, *values):
    dbcur.execute(stmt, *values)

def sql_insert(table, returning, **values):
    flat_values = [(column, value) for column, value in values.items()]
    stmt = 'INSERT INTO %s (%s) VALUES (%s)%s' % \
           (table,
            ', '.join([v[0] for v in flat_values]),
            ', '.join(['%s' for v in flat_values]),
            ' RETURNING %s' % returning if returning else '')
    sql(stmt, [v[1] for v in flat_values])
    if returning:
        return dbcur.fetchall()[0]

def filter_known(str):
    return None if str == 'n/a' or str == 'N/A' or str == 'unknown' else str

def insert_people():
    sql('DROP TABLE IF EXISTS people')
    sql("""CREATE TABLE people (
    id text PRIMARY KEY,
    name text NOT NULL,
    height text,
    mass text,
    hair_color text,
    skin_color text,
    eye_color text,
    birth_year text,
    gender text
    )""")
    for person in data['people']:
        sql_insert('people', 'id',
                   id=person['url'],
                   name=person['name'],
                   height=filter_known(person['height']),
                   mass=filter_known(person['mass']),
                   hair_color=filter_known(person['hair_color']),
                   eye_color=filter_known(person['eye_color']),
                   birth_year=filter_known(person['birth_year']),
                   gender=filter_known(person['gender']))

def insert_planets():
    sql('DROP TABLE IF EXISTS planets')
    sql("""CREATE TABLE planets (
    id text PRIMARY KEY,
    name text NOT NULL,
    rotation_period text,
    orbital_period text,
    diameter text,
    climate text,
    gravity text,
    terrain text,
    surface_water text,
    population text
    )""")
    for planet in data['planets']:
        sql_insert('planets', 'id',
                   id=planet['url'],
                   name=planet['name'],
                   rotation_period=filter_known(planet['rotation_period']),
                   orbital_period=filter_known(planet['orbital_period']),
                   diameter=filter_known(planet['diameter']),
                   climate=filter_known(planet['climate']),
                   gravity=filter_known(planet['gravity']),
                   terrain=filter_known(planet['terrain']),
                   surface_water=filter_known(planet['surface_water']),
                   population=filter_known(planet['population']))

insert_people()
insert_planets()

dbconn.commit()
