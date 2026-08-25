from datetime import date, timedelta
import requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)




def valid_intermpresas(days=60,which="PS"):
    today = date.today()
    for i in range(days):
        dt = today - timedelta(days=i)
        url = f"https://www.interempresas.net/Boletin/NL/{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/"+which+".html"
        try:
            r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10, verify=False)
            valid = r.status_code == 200 and "Ruta de acceso no encontrada" not in r.text and len(r.text.strip()) > 80
        except:
            valid = False
        if valid:
            return url
        #else:
        #    print("Invalid:", url)
    return None

print(valid_intermpresas(60,"Pa"))



