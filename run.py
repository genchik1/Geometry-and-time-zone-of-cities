#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time

import subprocess
from multiprocessing import Process

import click
from zipfile import ZipFile
import pandas as pd
import geopandas as gpd

import countries as c
import locomizer as l

from shapely.geometry import Point, box
from shapely.wkt import loads


def config():
    cliKey = str(input("Enter osm cliKey:"))
    with open('cliKeyOSM', 'w+') as file:
        file.write(cliKey)


def get_country_code(country):
    for keys, value in c.country.items():
        for key in keys:
            if country.lower() == key.lower():
                return value, keys[-1]


def _subproc(cliKey, output, country_code, lvl):
    curl = f"""curl -f -o {output} --url 'https://wambachers-osm.website/boundaries/exportBoundaries?cliVersion=1.0&cliKey={cliKey}&exportFormat=shp&exportLayout=levels&exportAreas=land&from_al={lvl}&to_al={lvl}&union=false&selected={country_code}'"""
    print (curl)
    subprocess.check_call(curl, shell=True, universal_newlines=False)


def export_boundaries(output, country_code, from_al, to_al):
    cliKey = open('cliKeyOSM').readline()
    for lvl in range(from_al, to_al+1):
        print (f"\nExport osm boundaries lvl: {lvl}")
        output_new = output + f'_lvl-{lvl}.zip'
        _subproc(cliKey, output_new, country_code, lvl)
        # with ZipFile(output_new, 'r') as zipObj:
        #     zipObj.extractall(output_new.replace('.zip', ''))


def langs(translator, string):
    string_lang = translator.detect(string).lang
    if string_lang != 'en':
        string = translator.translate(string)
    return string


@click.command()
@click.argument('operation')
@click.option('--country', '-c', type=str, default=None)
@click.option('--city', type=str, default=None)
@click.option('--lvl', type=str, default=None)
@click.option('--from_al', type=int, default=None)
@click.option('--to_al', type=int, default=None)
@click.option('--prefix', type=str, default=None)
def main(operation, country, from_al, to_al, city, lvl, prefix):
    if operation == 'config':
        config()

    if operation == 'export_boundaries':
        path_output = 'osm_boundaries_shp'
        if not os.path.exists(path_output):
            os.makedirs(path_output)

        assert os.path.isfile('cliKeyOSM'), "Perform the operation: 'python run.py config'"

        if country is None:
            country = input("Enter country: ")
        if from_al is None:
            from_al = input("Enter from_al: ")
        if to_al is None:
            to_al = input("Enter to_al: ")

        country_code, country_name = get_country_code(country)
        export_boundaries(os.path.join(path_output, country_name, country_name), country_code, from_al, to_al)

    if operation == 'get_geom':
        if country is None:
            country = input("Enter country: ")
        if city is None:
            city = input("Enter city: ")
        if lvl is None:
            lvl = input("Enter lvl: ")
            if lvl == '': lvl = None
        if prefix is None:
            prefix = input("Enter prefix: ")
            if prefix == '': prefix = None
        print(prefix)

        if os.path.exists(city):
            city = pd.read_csv(city, index_col=None, header=None, names=['cities', 'enname'])
            city = city['cities'].str.lower().tolist()
        else:
            city = [city.lower()]

        country_code, country_name = get_country_code(country)
        paths = []
        if lvl is None:
            for folder in os.listdir('osm_boundaries_shp'):
                if folder.startswith(country_name):
                    paths.append(os.path.join('osm_boundaries_shp', folder))
        else:
            paths.append(os.path.join('osm_boundaries_shp', country_name+'_lvl-'+lvl))

        result = pd.DataFrame()
        for path in paths:
            data = gpd.read_file(path)
            columns = data.columns
            data['locname'] = data['locname'].str.lower()
            if prefix is not None:
                data['l'] = data['locname'].str.startswith(prefix)
                data = data[data['l']==True]
                print (data.head())
            for _city in city:
                data['I'] = data['locname'].str.contains('\s'+_city+'$', regex=True)
                df = data[data['I']==True]
                if len(df)>0:
                    df['name'] = _city.title()
                    try:
                        lat, lon = l.geolocate(city=_city, country=country_name)
                        df['tz'] = l.tz_from_coordinates(lat,lon)
                        df['center'] = Point(lon, lat)
                        df['box'] = df['geometry'].apply(lambda x: x.bounds)
                        df['al'] = '6'
                        print (df[['name', 'tz', 'al', 'enname', 'locname', 'center', 'box', 'geometry']])
                        df.to_csv('test/cities_rus2.csv', sep=',', index=None, header=None, mode='a')
                        result = result.append(df[['name', 'tz', 'al', 'enname', 'locname', 'center', 'box', 'geometry']], ignore_index=True)
                    except TypeError:
                        continue
                    except ValueError:
                        continue
        result = gpd.GeoDataFrame(result, crs={'init': 'epsg:4326'}, geometry=result['geometry'])
        result.to_file('test/cities_rus3.geojson', driver="GeoJSON")

    if operation == 'read':
        data = gpd.read_file('test/cities_rus2.geojson')
        for df in data.to_dict('records'):
            print (df)
            raise SystemExit


    if operation == 'h3':
        data = pd.read_csv('test/cities_rus2.csv', index_col=None, header=None, prefix='X')
        names = pd.read_csv('test/cities', index_col=None, header=None, names=['cities', 'enname'])
        print (data.head())
        data = data.merge(names, right_on='cities', left_on='X12')

        for df in data.to_dict('records'):
            geo = loads(df['X15'])




if __name__ == "__main__":
    main()
