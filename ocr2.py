import os, sys
import scraperwiki, urllib2
from bs4 import BeautifulSoup
import requests
import csv


def send_Request(url):
#Get content, regardless of whether an HTML, XML or PDF file
    pageContent = urllib2.urlopen(url)
    return pageContent

def process_PDF(fileLocation):
#Use this to get PDF, covert to XML
    pdfToProcess = send_Request(fileLocation)
    pdfToObject = scraperwiki.pdftoxml(pdfToProcess.read())
    return pdfToObject

def parse_HTML_tree(contentToParse):
#returns a navigatibale tree, which you can iterate through
    soup = BeautifulSoup(contentToParse)
    return soup

base_url = "http://ceoharyana.nic.in/?module=draftroll"

response = requests.get(base_url)
base_soup = BeautifulSoup(response.content)

all_districts = base_soup.find('select', {'id': 'district'})
all_district_node = all_districts.findAll('option')
for district_node in all_district_node[-4:5:-1]:
    print district_node
    if district_node['value'] != '0':
        district_name = district_node.text
        district_value = district_node['value']
        csv_file = open("hardata/{}.csv".format(district_name), 'wt')
        writer = csv.writer(csv_file)
        fieldnames = ("District", "Constituency", "Polling Station", "Total", "Male", "Female", "PDF Link")
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        cons_url = "http://ceoharyana.nic.in/directs/check_draft.php?Type=dist&ID={}".format(district_value)
        cons_response = requests.get(cons_url)
        cons_soup = BeautifulSoup(cons_response.content)
        all_cons = cons_soup.findAll('option')
        for cons in all_cons:
            data_dict = {}
            if cons['value'] != '0':
                cons_name = cons.text
                cons_value = cons['value']
                data_dict[district_name] = {cons_name: {},}

                station_url = "http://ceoharyana.nic.in/directs/check_draft.php?Type=ac&ID={}".format(cons_value)
                station_response = requests.get(station_url)
                station_soup = BeautifulSoup(station_response.content)
                all_station = station_soup.findAll('option')
                for station in all_station:
                    if station['value'] != '0':
                        station_name = station.text
                        station_value = station['value']
                        pdf_link = "http://ceoharyana.nic.in/directs/check_draft.php?Type=pdf&ID={}".format(station_value)

                        for i in range(7):
                            try:
                                pdf_link_response = requests.get(pdf_link)
                                break
                            except:
                                import time
                                time.sleep(10)

                        pdf_link_soup = BeautifulSoup(pdf_link_response.content)
                        final_link = pdf_link_soup.find('a')['href']
                        pdf = process_PDF(final_link)
                        pdfToSoup = parse_HTML_tree(pdf)
                        soupToArray = pdfToSoup.findAll('text')
                        total = ""
                        male = ""
                        female = ""

                        for line in soupToArray:
                            left = int(line['left'])
                            top = int(line['top'])

                            if (left >= 350 and left <=372 ) and line['top'] == '1098':
                                total = line.text

                            if (left >= 485 and left <=500 ) and line['top'] == '1116':
                                male = line.text

                            if (left >= 580 and left <=602 ) and line['top'] == '1116':
                                female = line.text


                        station_modified_name = station_name.split("(")[0]

                        try:
                            if not data_dict.get(district_name).get(cons_name).get(station_modified_name):
                                temp_data_dict = {
                                    "Total": int(total),
                                    "Male": int(male),
                                    "Female": int(female),
                                    "pdf_link": [final_link]
                                }
                                data_dict[district_name][cons_name][station_modified_name] = temp_data_dict
                            else:
                                all_pdf_link = data_dict[district_name][cons_name][station_modified_name]['pdf_link']
                                all_pdf_link.append(final_link)
                                temp_data_dict = {
                                    "Total": int(data_dict[district_name][cons_name][station_modified_name]['Total']) + int(total),
                                    "Male": int(data_dict[district_name][cons_name][station_modified_name]['Male']) + int(male),
                                    "Female": int(data_dict[district_name][cons_name][station_modified_name]['Female']) + int(female),
                                    "pdf_link": all_pdf_link
                                }

                                data_dict[district_name][cons_name][station_modified_name] = temp_data_dict
                        except:
                            temp_data_dict = {
                                "Total": "",
                                "Male": "",
                                "Female": "",
                                "pdf_link": [final_link]
                            }
                            data_dict[district_name][cons_name][station_modified_name] = temp_data_dict

                        print temp_data_dict
                        os.system('rm /tmp/*.png')
                print data_dict
                for district_key, district_data in data_dict.iteritems():
                    for cons_key, cons_data in district_data.iteritems():
                        for station_key, station_data in cons_data.iteritems():
                            data_dict = {
                                'District': district_key,
                                'Constituency': cons_key,
                                'Polling Station': station_key,
                                "Total": station_data['Total'],
                                "Male": station_data['Male'],
                                "Female": station_data['Female'],
                                "PDF Link": (", ").join(station_data['pdf_link']),
                            }
                            try:
                                writer.writerow(data_dict)
                            except:
                                data_dict['Total'] = ''
                                data_dict['Male'] = ''
                                data_dict['Female'] = ''
                                writer.writerow(data_dict)
