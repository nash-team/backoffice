# Configuration ComfyUI avec Qwen Image Edit 2509

Ce guide explique comment configurer ComfyUI pour utiliser la fonctionnalité d'édition d'images avec Qwen.

## 📋 Prérequis

1. **ComfyUI installé** et fonctionnel (http://127.0.0.1:8188)
2. **Modèle Qwen2-VL** téléchargé
3. **Espace disque** : ~5-10 GB pour le modèle

## 🔧 Installation pas à pas

### 1. Télécharger le modèle Qwen2-VL

```bash
# Aller dans le dossier des checkpoints de ComfyUI
cd ComfyUI/models/checkpoints/

# Télécharger Qwen2-VL-2B (version légère recommandée)
wget https://huggingface.co/Qwen/Qwen2-VL-2B/resolve/main/qwen2-vl-2b.safetensors
```

**Alternative** : Tu peux aussi télécharger manuellement depuis HuggingFace :
- https://huggingface.co/Qwen/Qwen2-VL-2B

### 2. Vérifier la structure du workflow

Le fichier `qwen-edit-workflow.json` est déjà configuré avec :

- **Node 1** : LoadImage - charge l'image à éditer
- **Node 2** : CLIPTextEncode - reçoit le prompt d'édition
- **Node 3** : KSampler - applique l'édition
- **Node 4** : CheckpointLoaderSimple - charge Qwen2-VL
- **Node 5** : Negative prompt (vide par défaut)
- **Node 6** : VAEEncode - encode l'image en latent
- **Node 7** : VAEDecode - décode l'image éditée
- **Node 8** : SaveImage - sauvegarde le résultat

### 3. Tester manuellement dans ComfyUI

1. **Ouvre ComfyUI** : http://127.0.0.1:8188
2. **Charge le workflow** : "Load" → `qwen-edit-workflow.json`
3. **Upload une image** : Node 1 (LoadImage)
4. **Entre un prompt** : Node 2 (ex: "replace 5 toes with 3 toes")
5. **Queue Prompt** pour tester

### 4. Configurer models.yaml

Assure-toi que ton `config/generation/models.yaml` utilise ComfyUI :

```yaml
coloring_page:
  provider: comfy
  model: qwen-edit-workflow.json  # Utilisé pour l'édition aussi
```

## 🎯 Test rapide de l'édition

Une fois tout configuré :

1. **Lance ComfyUI** :
   ```bash
   cd ComfyUI
   python main.py
   ```

2. **Lance l'app** :
   ```bash
   make run
   ```

3. **Teste l'édition** :
   - Va sur un ebook en mode DRAFT
   - Clique sur "Modifier" sur une page
   - Dans le modal, entre un prompt de correction (ex: "remplace les 5 doigts par 3 doigts")
   - Clique sur "Éditer"
   - La preview devrait s'afficher avec l'image éditée

## 🔍 Paramètres ajustables

Dans `qwen-edit-workflow.json`, node 3 (KSampler) :

- **steps** : 20 par défaut (plus = meilleure qualité, plus lent)
- **cfg** : 7.0 par défaut (contrôle la force du prompt)
- **denoise** : 0.75 par défaut (0.0 = pas de changement, 1.0 = changement total)

**Pour des corrections légères** : diminue `denoise` à 0.5-0.6
**Pour des changements majeurs** : augmente `denoise` à 0.8-1.0

## ❌ Dépannage

### Erreur "qwen2-vl-2b.safetensors not found"
→ Vérifie que le modèle est bien dans `ComfyUI/models/checkpoints/`

### Erreur "workflow not found"
→ Vérifie que `qwen-edit-workflow.json` existe dans `config/generation/comfy/`

### ComfyUI timeout
→ Vérifie que ComfyUI est bien lancé sur http://127.0.0.1:8188

### Image upload failed
→ Vérifie que le dossier `ComfyUI/input/edit_inputs/` existe (créé automatiquement)

## 🎨 Exemples de prompts d'édition

- "replace 5 toes with 3 toes on the dinosaur"
- "add spots on the dinosaur body"
- "remove the cloud in the background"
- "change the tree to a palm tree"
- "make the dinosaur smile"

## 📚 Ressources

- Qwen2-VL sur HuggingFace : https://huggingface.co/Qwen/Qwen2-VL-2B
- ComfyUI docs : https://github.com/comfyanonymous/ComfyUI
- Qwen Image Edit 2509 : https://qwenlm.github.io/blog/qwen2-vl/

## ⚡ Alternative : Utiliser Gemini à la place

Si tu ne veux pas installer Qwen, tu peux utiliser Gemini à la place :

```yaml
# config/generation/models.yaml
coloring_page:
  provider: gemini
  model: gemini-2.5-flash-image
```

Puis configure la clé API :
```bash
export GEMINI_API_KEY="ta-cle-api"
```

Gemini fonctionnera directement sans workflow ComfyUI !
