import requests
from bs4 import BeautifulSoup

def xml_river(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    with open("response.txt", "w") as file:
        file.write(soup.text)
    return soup.text

if __name__ == "__main__":
    xml_river("http://xmlriver.com/wordstat/json?user=16705&key=c9fa00b3e6cebd7787b193ed2f2afb316ab931ff&query=test")