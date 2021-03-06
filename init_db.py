#!/usr/bin/env python3

import json
import psycopg2
import requests
import os
import uuid

from psycopg2.extras import Json

psycopg2.extras.register_uuid()

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

uuid_registry = {}

def id_to_uuid(id):
    global uuid_registry
    if not id in uuid_registry:
        uuid_registry[id] = uuid.uuid4()

    return uuid_registry[id]

def filter_known(str):
    return None if str == 'n/a' or str == 'N/A' or str == 'unknown' else str

class Column:
    def __init__(self, name, sql_type='text', source_key=None, not_null=False, references=None, map_id=False):
        self.name = name
        self.sql_type = sql_type
        self.not_null = not_null
        self.source_key = source_key or name
        self.references = references
        self.map_id = map_id

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
            value = item[self.source_key]
        else:
            value = filter_known(item[self.source_key])

        if self.map_id and value:
            value = str(id_to_uuid(value))

        return value

def raw_sql():
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

    def define_resource_table(name, items, *columns):
        columns_str = ', '.join(map(lambda column: column.sql_def, columns))
        create = 'CREATE TABLE %s (id text PRIMARY KEY, %s)' % (name, columns_str)

        sql(create)

        for item in items:
            kw = {}
            kw['id'] = str(id_to_uuid(item['url']))
            for column in columns:
                kw[column.name] = column.value(item)
            sql_insert(name, 'id', **kw)

    def define_edge_table(name, source_table, source_data, fields_fn, target_table):
        create = """CREATE TABLE %s (
        %s_id text REFERENCES %s (id) ON UPDATE CASCADE ON DELETE CASCADE,
        %s_id text REFERENCES %s (id) ON UPDATE CASCADE
        )""" % (name, source_table, source_table, target_table, target_table)

        sql(create)

        for item in source_data:
            for target_id in fields_fn(item):
                kw = {}
                kw['%s_id' % source_table] = str(id_to_uuid(item['url']))
                kw['%s_id' % target_table] = str(id_to_uuid(target_id))
                sql_insert(name, None, **kw)

    print('start drop tables')

    sql('DROP TABLE IF EXISTS person_lifeforms')
    sql('DROP TABLE IF EXISTS person_films')
    sql('DROP TABLE IF EXISTS planet_films')
    sql('DROP TABLE IF EXISTS starship_films')
    sql('DROP TABLE IF EXISTS vehicle_films')
    sql('DROP TABLE IF EXISTS lifeform_films')
    sql('DROP TABLE IF EXISTS starship_pilots')
    sql('DROP TABLE IF EXISTS vehicle_pilots')

    sql('DROP TABLE IF EXISTS vehicle')
    sql('DROP TABLE IF EXISTS starship')
    sql('DROP TABLE IF EXISTS film')
    sql('DROP TABLE IF EXISTS person')
    sql('DROP TABLE IF EXISTS lifeform')
    sql('DROP TABLE IF EXISTS planet')

    define_resource_table('planet', data['planets'],
                          Column('name', not_null=True),
                          Column('population'),
                          Column('terrain'),
                          Column('climate'),
                          Column('rotation_period'),
                          Column('orbital_period'),
                          Column('diameter'),
                          Column('gravity'),
                          Column('surface_water'))

    define_resource_table('lifeform', data['species'],
                          Column('name', not_null=True),
                          Column('classification', not_null=True),
                          Column('designation'),
                          Column('language'),
                          Column('average_height'),
                          Column('average_lifespan'),
                          Column('homeworld', map_id=True, references='planet'))

    define_resource_table('person', data['people'],
                          Column('name', not_null=True),
                          Column('height'),
                          Column('mass'),
                          Column('hair_color'),
                          Column('skin_color'),
                          Column('eye_color'),
                          Column('birth_year'),
                          Column('gender'),
                          Column('homeworld', map_id=True, references='planet'))

    define_resource_table('film', data['films'],
                          Column('title', not_null=True),
                          Column('director', not_null=True),
                          Column('producer'),
                          Column('release_date'),
                          Column('opening_crawl'))

    define_resource_table('starship', data['starships'],
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

    define_resource_table('vehicle', data['vehicles'],
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

    define_edge_table('person_films', 'person', data['people'], lambda person: person['films'], 'film')
    define_edge_table('planet_films', 'planet', data['planets'], lambda planet: planet['films'], 'film')
    define_edge_table('starship_films', 'starship', data['starships'], lambda starship: starship['films'], 'film')
    define_edge_table('vehicle_films', 'vehicle', data['vehicles'], lambda vehicle: vehicle['films'], 'film')
    define_edge_table('lifeform_films', 'lifeform', data['species'], lambda species: species['films'], 'film')

    define_edge_table('starship_pilots', 'starship', data['starships'], lambda starship: starship['pilots'], 'person')
    define_edge_table('vehicle_pilots', 'vehicle', data['vehicles'], lambda vehicle: vehicle['pilots'], 'person')

    define_edge_table('person_lifeforms', 'person', data['people'], lambda person: person['species'], 'lifeform')

    dbconn.commit()

raw_sql()
