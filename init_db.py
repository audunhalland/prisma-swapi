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
    'films': swapi_list_resource_cached('https://swapi.co/api/films'),
    'starships': swapi_list_resource_cached('https://swapi.co/api/starships'),
    'vehicles': swapi_list_resource_cached('https://swapi.co/api/vehicles'),
    'species': swapi_list_resource_cached('https://swapi.co/api/species'),
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

class Column:
    def __init__(self, name, sql_type='text', source_key=None, not_null=False, references=None):
        self.name = name
        self.sql_type = sql_type
        self.not_null = not_null
        self.source_key = source_key or name
        self.references = references

    @property
    def sql_def(self):
        s = self.name
        s += ' '
        s += self.sql_type
        if self.not_null:
            s += ' NOT NULL'
        if self.references:
            s += ' REFERENCES %s (id)' % self.references
        return s

    def value(self, item):
        if self.not_null:
            return item[self.source_key]
        else:
            return filter_known(item[self.source_key])

def define_resource_table(name, items, *columns):
    columns_str = ', '.join(map(lambda column: column.sql_def, columns))
    create = 'CREATE TABLE %s (id text PRIMARY KEY, %s)' % (name, columns_str)

    sql('DROP TABLE IF EXISTS %s' % name)
    sql(create)

    for item in items:
        kw = {}
        kw['id'] = item['url']
        for column in columns:
            kw[column.name] = column.value(item)
        sql_insert(name, 'id', **kw)

define_resource_table('planets', data['planets'],
                      Column('name', not_null=True),
                      Column('population'),
                      Column('terrain'),
                      Column('climate'),
                      Column('rotation_period'),
                      Column('orbital_period'),
                      Column('diameter'),
                      Column('gravity'),
                      Column('surface_water'))

define_resource_table('species', data['species'],
                      Column('name', not_null=True),
                      Column('classification', not_null=True),
                      Column('designation'),
                      Column('language'),
                      Column('average_height'),
                      Column('average_lifespan'),
                      Column('homeworld', references='planets'))

define_resource_table('people', data['people'],
                      Column('name', not_null=True),
                      Column('height'),
                      Column('mass'),
                      Column('hair_color'),
                      Column('skin_color'),
                      Column('eye_color'),
                      Column('birth_year'),
                      Column('gender'),
                      Column('homeworld', references='planets'))

define_resource_table('films', data['films'],
                      Column('title', not_null=True),
                      Column('director', not_null=True),
                      Column('producer'),
                      Column('release_date'),
                      Column('opening_crawl'))

define_resource_table('starships', data['starships'],
                      Column('name', not_null=True),
                      Column('starship_class', not_null=True),
                      Column('model'),
                      Column('manufacturer'),
                      Column('length'),
                      Column('MGLT'),
                      Column('consumables'),
                      Column('cost_in_credits'),
                      Column('crew'),
                      Column('hyperdrive_rating'),
                      Column('passengers'))

define_resource_table('vehicles', data['vehicles'],
                      Column('name', not_null=True),
                      Column('vehicle_class', not_null=True),
                      Column('model'),
                      Column('manufacturer'),
                      Column('length'),
                      Column('consumables'),
                      Column('cost_in_credits'),
                      Column('crew'),
                      Column('passengers'),
                      Column('max_atmosphering_speed'))

dbconn.commit()
