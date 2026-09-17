#pip install py3langid

from py3langid import classify

def is_english(text):
    return bool(text) and classify(text)[0] == "en"


articles = [
    "Städte verändern sich schnell. Neue Technologien, nachhaltiger Verkehr und moderne Gebäude werden das urbane Leben prägen. Elektrofahrzeuge, öffentliche Verkehrsmittel und mehr Grünflächen können die Umwelt verbessern. Gleichzeitig müssen Städte bezahlbaren Wohnraum schaffen und soziale Bedürfnisse berücksichtigen. Die Stadt der Zukunft sollte daher nicht nur intelligenter, sondern auch nachhaltiger, zugänglicher und lebenswerter sein.",
    
    "Les espaces verts jouent un rôle essentiel dans les villes. Les arbres et les parcs améliorent la qualité de l’air, réduisent les températures et offrent des lieux de détente. Ils favorisent également les rencontres et l’activité physique. Avec le changement climatique, les villes devront donc intégrer davantage de nature dans leur développement urbain.",
    
    "El mundo del trabajo está cambiando rápidamente. El teletrabajo, la inteligencia artificial y las herramientas digitales están transformando las empresas. Estas tecnologías permiten trabajar de forma más flexible y automatizar determinadas tareas. Sin embargo, también requieren nuevas competencias. En el futuro, la creatividad, la adaptación y la capacidad para resolver problemas serán cada vez más importantes."
]


for article in articles:
    if is_english(article):
        print(article[:50]+str(" ....is English"))
    else:
        print(article[:50]+str(" ....is not English"))