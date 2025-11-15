# Guide de Configuration YAML

Ce guide explique comment modifier les configurations du système sans toucher au code Python.

## 📁 Structure des fichiers de configuration

```
config/
├── kdp/
│   └── specifications.yaml    # Specs Amazon KDP (formats, papier, etc.)
└── business/
    └── limits.yaml            # Contraintes métier (pages, images, etc.)
```

## 📐 KDP Specifications (`config/kdp/specifications.yaml`)

### Ajouter un nouveau format de livre

```yaml
formats:
  mon_nouveau_format:
    name: "Mon Format Custom"
    trim_size_inches:
      width: 6.0
      height: 9.0
    bleed_inches: 0.125
    dpi: 300
    margins_inches:
      top: 0.5
      bottom: 0.5
      inner: 0.75
      outer: 0.5
```

**Utilisation :**
```python
kdp_config = KDPExportConfig(
    trim_size=config.get_kdp_trim_size("mon_nouveau_format")
)
```

### Ajouter un nouveau type de papier

```yaml
paper_types:
  ultra_premium:
    display_name: "Ultra Premium (80lb)"
    spine_formula: 0.0026
    min_pages: 24
    max_pages: 600
    cost_factor: 1.5
```

**Utilisation :**
```python
kdp_config = KDPExportConfig(paper_type="ultra_premium")
# ✅ Validation automatique contre le YAML
```

### Ajouter une nouvelle finition de couverture

```yaml
cover:
  finish_types:
    premium_glossy:
      name: "Premium Glossy"
      cost_factor: 1.3
```

**Utilisation :**
```python
kdp_config = KDPExportConfig(cover_finish="premium_glossy")
```

### Modifier les valeurs par défaut

```yaml
defaults:
  format: "large_coloring_book"      # Au lieu de square_format
  paper_type: "standard_color"       # Au lieu de premium_color
  cover_finish: "matte"              # Au lieu de glossy
  include_barcode: false             # Au lieu de true
```

**Effet immédiat :**
```python
# Sans arguments, utilise les defaults du YAML
kdp_config = KDPExportConfig()
print(kdp_config.paper_type)  # "standard_color"
print(kdp_config.cover_finish)  # "matte"
```

## 📊 Business Limits (`config/business/limits.yaml`)

### Modifier les limites de pages

```yaml
ebook:
  pages:
    min: 20   # Au lieu de 24
    max: 50   # Au lieu de 30
```

**Effet :**
```python
from backoffice.features.ebook.shared.domain.constants import MIN_PAGES, MAX_PAGES
print(MIN_PAGES)  # 20
print(MAX_PAGES)  # 50
```

### Modifier les contraintes d'images

```yaml
images:
  cover:
    min_pixels: 3000  # Au lieu de 2550

  content:
    min_pixels: 2400  # Au lieu de 2175
```

## 🔍 Validation automatique

Le système valide automatiquement les valeurs au runtime :

```python
# ❌ Erreur si valeur invalide
kdp_config = KDPExportConfig(paper_type="invalid_type")
# ValueError: Invalid paper_type: 'invalid_type'.
#             Must be one of: premium_color, standard_color, white, cream.
#             Check config/kdp/specifications.yaml
```

## 💰 Calculs de coûts

Les `cost_factor` permettent de calculer les prix :

```python
config = ConfigLoader()

# Coût papier
paper_cost = base_price * config.get_paper_type_cost_factor("premium_color")  # 1.2x

# Coût finition
finish_cost = base_price * config.get_cover_finish_cost_factor("matte")  # 1.1x
```

## 📏 Règles de validation

Modifier les règles de validation sans toucher au code :

```yaml
validation:
  cover:
    min_resolution_px: 3000  # Augmenter la qualité requise
    min_dpi: 350            # Au lieu de 300
    max_file_size_mb: 800   # Au lieu de 650

  filenames:
    pattern: "^[a-zA-Z0-9_-]+$"
    max_length: 150  # Au lieu de 100
```

## 🎨 Profils couleur

Changer les profils ICC :

```yaml
color_profiles:
  rgb:
    profile: "AdobeRGB.icc"  # Au lieu de sRGB
    description: "Adobe RGB for wider gamut"
```

## 📤 Export PDF

Modifier les paramètres d'export :

```yaml
export:
  pdf_version: "1.7"  # Au lieu de 1.4
  embed_fonts: true
  compress_images: true
  compression_quality: 0.98  # Au lieu de 0.95 (meilleure qualité)
```

## ✅ Bonnes pratiques

1. **Toujours tester après modification** :
   ```bash
   make test-unit
   ```

2. **Utiliser des noms descriptifs** :
   ```yaml
   # ❌ Mauvais
   ultra_p:
     display_name: "UP"

   # ✅ Bon
   ultra_premium:
     display_name: "Ultra Premium Color (80lb)"
   ```

3. **Documenter les valeurs** :
   ```yaml
   spine_formula: 0.002347  # inches per page (KDP official)
   ```

4. **Versionner les changements** (git) :
   ```bash
   git add config/
   git commit -m "Add ultra_premium paper type"
   ```

## 🚀 Exemples d'utilisation

### Créer une config custom pour un projet spécial

```python
from backoffice.config import ConfigLoader

config = ConfigLoader()

# Format large + papier premium + finition matte
kdp_config = KDPExportConfig(
    trim_size=config.get_kdp_trim_size("large_coloring_book"),  # 8.5x11
    paper_type="premium_color",
    cover_finish="matte",
)
```

### Afficher toutes les options disponibles

```python
config = ConfigLoader()

print("Formats:", config.get_valid_formats())
print("Papers:", config.get_valid_paper_types())
print("Finishes:", config.get_valid_cover_finishes())

# Formats: ['standard_coloring_book', 'large_coloring_book', 'square_format']
# Papers: ['premium_color', 'standard_color', 'white', 'cream']
# Finishes: ['glossy', 'matte']
```

### Utiliser les display names dans l'UI

```python
for paper_type in config.get_valid_paper_types():
    display_name = config.get_paper_type_display_name(paper_type)
    print(f"{paper_type} → {display_name}")

# premium_color → Premium Color (70lb)
# standard_color → Standard Color (60lb)
# white → Black & White (55lb)
# cream → Cream (55lb)
```

## 📞 Support

Si une valeur YAML est invalide, le système échoue au démarrage avec un message clair :

```
FileNotFoundError: Config file not found: /path/to/config/kdp/specifications.yaml
```

Ou si une valeur est utilisée incorrectement :

```
ValueError: Invalid paper_type: 'ultra_premium'.
Must be one of: premium_color, standard_color, white, cream.
Check config/kdp/specifications.yaml
```

---

**Résumé : Plus besoin de toucher au code Python pour modifier les specs KDP ! 🎉**
