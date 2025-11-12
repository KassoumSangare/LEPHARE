# Documentation API - Gestion des Devis

## Authentification

Tous les endpoints nécessitent une authentification par token.

**Header requis :**
```
Authorization: Token <votre_token>
```

---

## Endpoints

### 1. Récupérer les devis d'un client pour un produit

Récupère la liste des devis associés à un client spécifique pour un produit donné.

**Méthode :** `GET`

**URL :** `/api/devisclient/`

#### Paramètres de requête

| Paramètre | Type | Obligatoire | Description |
|-----------|------|-------------|-------------|
| `idclient` | integer | Oui | Identifiant du client |
| `idproduit` | integer | Oui | Identifiant du produit |

#### Exemple de requête

```http
GET http://localhost:8000/api/devisclient/?idclient=61&idproduit=1
Authorization: Token <votre_token>
```

#### Réponse en cas de succès

**Code :** `200 OK`

**Corps de la réponse :**

```json
[
  {
    "iddevis": 449,
    "numerodevis": "118620124D0144L",
    "nomclient": "ADOU FADIDOU BALLARD"
  },
  {
    "iddevis": 636,
    "numerodevis": "118620124D0206A",
    "nomclient": "ADOU FADIDOU BALLARD"
  },
  {
    "iddevis": 231,
    "numerodevis": "118620524D0084C",
    "nomclient": "ADOU FADIDOU BALLARD"
  }
]
```

**Si aucun devis trouvé :**

```json
[]
```

#### Réponses d'erreur

| Code | Description |
|------|-------------|
| `400 Bad Request` | Paramètres manquants ou invalides |
| `401 Unauthorized` | Token d'authentification manquant ou invalide |

---

### 2. Consolider plusieurs devis

Permet de consolider plusieurs devis existants en un seul nouveau devis. Les devis à consolider doivent appartenir au même client et au même produit.

**Méthode :** `POST`

**URL :** `/api/consolidationdevis/`

#### Corps de la requête

**Format :** JSON

**Structure :**

```json
[
  { "iddevis": 449 },
  { "iddevis": 636 },
  { "iddevis": 231 }
]
```

**Contraintes :**
- Minimum 2 devis requis
- Les devis doivent appartenir au même client
- Les devis doivent concerner le même produit

#### Exemple de requête

```http
POST http://localhost:8000/api/consolidationdevis/
Authorization: Token <votre_token>
Content-Type: application/json

[
  { "iddevis": 449 },
  { "iddevis": 636 },
  { "iddevis": 231 }
]
```

#### Réponse en cas de succès

**Code :** `200 OK`

**Corps de la réponse :**

```json
{
  "iddevis": 789,
  "message": "Devis consolidés avec succès."
}
```

**Champs de la réponse :**

| Champ | Type | Description |
|-------|------|-------------|
| `iddevis` | integer | Identifiant du nouveau devis consolidé créé |
| `message` | string | Message de confirmation |

#### Réponses d'erreur

| Code | Description |
|------|-------------|
| `400 Bad Request` | Corps de requête invalide ou devis inexistants |
| `401 Unauthorized` | Token d'authentification manquant ou invalide |
| `403 Forbidden` | Les devis n'appartiennent pas au même client ou au même produit |

---

## Notes

- Tous les endpoints retournent des données au format JSON
- L'URL de base utilisée dans les exemples est `http://localhost:8000` (environnement de développement)
- Assurez-vous de remplacer `<votre_token>` par votre token d'authentification valide