from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import Optional, Any
import time
from datetime import datetime
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Autoriser toutes les origines (ou spécifier une liste d'origines)
    allow_credentials=True,
    allow_methods=["*"],  # Autoriser toutes les méthodes HTTP (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Autoriser tous les en-têtes
)

# Charger les variables d'environnement
load_dotenv()

# Configuration de la base de données à partir du fichier .env
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
LOG_COLLECTION_NAME = os.getenv("LOG_COLLECTION_NAME")

# Application FastAPI

# Fonction utilitaire pour convertir les documents MongoDB
def transform_mongo_document(doc):
    """Transforme un document MongoDB pour qu'il soit compatible avec le modèle Pydantic."""
    if doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc

class Enterprise(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    siren: Optional[Any]
    nic: Optional[Any]
    siret: Optional[Any]
    statutDiffusionEtablissement: Optional[Any]
    dateCreationEtablissement: Optional[Any]
    trancheEffectifsEtablissement: Optional[Any]
    anneeEffectifsEtablissement: Optional[Any]
    activitePrincipaleRegistreMetiersEtablissement: Optional[Any]
    dateDernierTraitementEtablissement: Optional[Any]
    etablissementSiege: Optional[Any]
    nombrePeriodesEtablissement: Optional[Any]
    complementAdresseEtablissement: Optional[Any]
    numeroVoieEtablissement: Optional[Any]
    indiceRepetitionEtablissement: Optional[Any]
    typeVoieEtablissement: Optional[Any]
    libelleVoieEtablissement: Optional[Any]
    codePostalEtablissement: Optional[Any]
    libelleCommuneEtablissement: Optional[Any]
    libelleCommuneEtrangerEtablissement: Optional[Any]
    distributionSpecialeEtablissement: Optional[Any]
    codeCommuneEtablissement: Optional[Any]
    codeCedexEtablissement: Optional[Any]
    libelleCedexEtablissement: Optional[Any]
    codePaysEtrangerEtablissement: Optional[Any]
    libellePaysEtrangerEtablissement: Optional[Any]
    complementAdresse2Etablissement: Optional[Any]
    numeroVoie2Etablissement: Optional[Any]
    indiceRepetition2Etablissement: Optional[Any]
    typeVoie2Etablissement: Optional[Any]
    libelleVoie2Etablissement: Optional[Any]
    codePostal2Etablissement: Optional[Any]
    libelleCommune2Etablissement: Optional[Any]
    libelleCommuneEtranger2Etablissement: Optional[Any]
    distributionSpeciale2Etablissement: Optional[Any]
    codeCommune2Etablissement: Optional[Any]
    codeCedex2Etablissement: Optional[Any]
    libelleCedex2Etablissement: Optional[Any]
    codePaysEtranger2Etablissement: Optional[Any]
    libellePaysEtranger2Etablissement: Optional[Any]
    dateDebut: Optional[Any]
    etatAdministratifEtablissement: Optional[Any]
    enseigne1Etablissement: Optional[Any]
    enseigne2Etablissement: Optional[Any]
    enseigne3Etablissement: Optional[Any]
    denominationUsuelleEtablissement: Optional[Any]
    activitePrincipaleEtablissement: Optional[Any]
    nomenclatureActivitePrincipaleEtablissement: Optional[Any]
    caractereEmployeurEtablissement: Optional[Any]

    class Config:
        allow_population_by_field_name = True  # Permet d'utiliser les alias en entrée/sortie
        json_encoders = {str: str}  # Permet de gérer l'encodage des types de base


# Classe pour les logs
class Log(BaseModel):
    request_type: str  # POST, GET, DELETE, PUT, etc.
    route: str  # Route lancée
    datetime: datetime  # Date et heure de la requête
    duration: float  # Durée de la requête en secondes
    response_code: int  # Code de la réponse HTTP
    method: str  # Méthode HTTP utilisée (GET, POST, etc.)
    ip_address: Optional[str]  # IP de l'utilisateur (optionnel)
    user_agent: Optional[str]  # User-agent (optionnel)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Client MongoDB avec Motor
client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]
logs_collection = db[LOG_COLLECTION_NAME]

# Middleware pour enregistrer les logs
@app.middleware("http")
async def log_request(request: Request, call_next):
    start_time = time.time()  # Enregistrement de l'heure de début
    
    # Traiter la requête
    response = await call_next(request)
    
    # Calculer la durée de la requête
    duration = time.time() - start_time
    
    # Enregistrer le log dans la base de données
    log = Log(
        request_type=request.method,
        route=str(request.url),
        datetime=datetime.utcnow(),
        duration=duration,
        response_code=response.status_code,
        method=request.method,
        ip_address=request.client.host,  # Récupérer l'IP de l'utilisateur
        user_agent=request.headers.get("User-Agent")  # Récupérer l'user-agent
    )
    
    # Insérer le log dans la collection MongoDB
    await logs_collection.insert_one(log.dict())
    
    # Retourner la réponse à l'utilisateur
    return response

# CRUD opérations pour les entreprises
@app.post("/enterprise/", response_model=Enterprise)
async def create_enterprise(enterprise: Enterprise):
    """Créer une nouvelle entreprise"""
    result = await collection.insert_one(enterprise.dict(exclude_unset=True))
    created_enterprise = await collection.find_one({"_id": result.inserted_id})
    return transform_mongo_document(created_enterprise)

@app.get("/enterprise/{siret}", response_model=Enterprise)
async def read_enterprise(siret: int):
    """Lire une entreprise à partir de son SIRET"""
    enterprise = await collection.find_one({"siret": siret})
    if enterprise is None:
        raise HTTPException(status_code=404, detail="Enterprise not found")
    return transform_mongo_document(enterprise)

@app.put("/enterprise/{siret}", response_model=Enterprise)
async def update_enterprise(siret: int, enterprise: Enterprise):
    """Mettre à jour une entreprise en fonction de son SIRET"""
    existing_enterprise = await collection.find_one({"siret": siret})
    if existing_enterprise is None:
        raise HTTPException(status_code=404, detail="Enterprise not found")
    
    update_result = await collection.update_one(
        {"siret": siret},
        {"$set": enterprise.dict(exclude_unset=True)}
    )
    if update_result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Enterprise not updated")
    
    updated_enterprise = await collection.find_one({"siret": siret})
    return transform_mongo_document(updated_enterprise)

@app.delete("/enterprise/{siret}", response_model=dict)
async def delete_enterprise(siret: int):
    """Supprimer une entreprise en fonction de son SIRET"""
    enterprise = await collection.find_one({"siret": siret})
    if enterprise is None:
        raise HTTPException(status_code=404, detail="Enterprise not found")
    
    await collection.delete_one({"siret": siret})
    return {"message": "Enterprise deleted successfully"}