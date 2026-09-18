import axios from 'axios'

// CREER UN CONTRAT
const createContrat = async (contratData, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'devis/', contratData, config)
    return response.data
}
// OBTENIR LES CONTRATS
const getContrats = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }

    const response = await axios.get(process.env.REACT_APP_API_URL + 'devis/', config)
    return response.data.results || response.data
}

// GET TARIFS DETAILS
const getTarifsdetails = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'tarifdetail/', config)
    return response.data.results || response.data
}

// GET TARIFS
const getTarifs = async (idproduit, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + `tarifparproduit/${idproduit}`, config)
    return response.data.data
}

// GET TARIFS
const getTarifsVoyage = async (idproduit, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + `tarifvoyage/${idproduit}`, config)
    return response.data.data
}


// GET GARANTIE
const getGaranties = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'garantie/', config)
    return response.data.results || response.data
}

// GET SOUS GARANTIE
const getSousgaranties = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'sousgarantie/', config)
    return response.data.results || response.data
}

// GET GARANTIE RISQUES
const getGarantierisques = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'garantierisque/', config)
    return response.data.results || response.data
}

// GET CATEGORIE
const getCategories = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'categorie/', config)
    return response.data.results || response.data
}

// GET BRANCHE
const getBranches = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'branche/', config)
    return response.data.results || response.data
}

// GET RISQUE
const getRisques = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'risque/', config)
    return response.data.results || response.data
}

// GET ENERGIE
const getEnergies = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'energie/', config)
    return response.data.results || response.data
}

// GET COMPAGNIE
const getCompagnies = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'compagnie/', config)
    return response.data.results || response.data
}

// GET QUALITE
const getQualites = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'qualite/', config)
    return response.data.results || response.data
}

const getOffres = async ({ idproduit, idtarif, token }) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        },
        params: {
            idproduit: idproduit,
            idtarif: idtarif
        }
    };
    const response = await axios.get(`${process.env.REACT_APP_API_URL}offreparproduit/`, config);
    return response.data.data;
};


// GET OFFRES VOYAGES
const getOffresVoyages = async (idproduit, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + `offrevoyage/${idproduit}`, config)
    return response.data.data
}

// GET OFFRES SANTE 
const getOffresSante = async (idtarif, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + `offresantepartarif/${idtarif}`, config)
    return response.data.data
}

// GET OFFRE DETAIL
const getOffredetails = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'offredetail/', config)
    return response.data.results || response.data
}

// GET MARQUE
const getMarques = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'marque/', config)
    return response.data.results || response.data
}

// GET SYSTEME SECURITE
const getSystemesecurites = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'systemesecurite/', config)
    return response.data.results || response.data
}

// GET CATEGORIE PERMIS
const getCategoriePermis = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'categoriepermis/', config)
    return response.data.results || response.data
}

// GET MODELE
const getModeles = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'modele/', config)
    return response.data.results || response.data
}


// GET USAGE
const getUsages = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'usage/', config)
    return response.data.results || response.data
}



// UPDATING
// GET TYPE VEHICULE
const getTypeVehicule = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'typevehicule/', config)
    return response.data.results || response.data
}

// GET GENRE VEHICULE
const getGenreVehicule = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'genrevehicule/', config)
    return response.data.results || response.data
}

// GET PROFESSION
const getProfession = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'profession/', config)
    return response.data.results || response.data
}


// GET PROFESSION IA
const getProfessionIA = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'professionia/', config)
    return response.data.results || response.data
}


// GET TYPE SOUSCRIPTEUR
const getTypeSouscripteur = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'typesouscripteur/', config)
    return response.data.results || response.data
}

// GET TYPE ASSURE
const getTypeAssure = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'typeassure/', config)

    const data = response.data
    const list =
        (Array.isArray(data) && data) ||
        (Array.isArray(data?.results) && data.results) ||
        (Array.isArray(data?.data) && data.data) ||
        (Array.isArray(data?.Data) && data.Data) ||
        []

    return list
}

// GET PAYS ZONE
const getPaysZone = async (idComp, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + `payszone/${idComp}`, config)
    return response.data.results || response.data
}

// GET PAYS
const getPays = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'pays', config)
    return response.data.results || response.data
}

//CarteBrume
// GET PAYS
// const getCarteBrume = async (token, id) => {
//     const config = {
//         headers: {
//             Authorization: `Token ${token}`
//         }
//     }
//     const response = await axios.get(process.env.REACT_APP_API_URL + `infovehicule/${id}`, config)
//     return response.data
// }

// GET QUALITES SOUSCRIPTEUR
const getQualitesSouscripteur = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'qualitesouscripteur/', config)
    return response.data.results || response.data
}

// GET COLLEGES
const getColleges = async (idoffre, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + `collegesanteparoffre/${idoffre}`, config)
    return response.data.results || response.data
}

// GET ZONE COUVERTURE
const getZoneCouvertureSante = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'zonecouverturesante/', config)
    return response.data.results || response.data
}


// EXPORT
const contratService = {
    createContrat,
    getContrats,
    // utils
    getTarifsdetails,
    getTarifs,
    getTarifsVoyage,
    getGaranties,
    getSousgaranties,
    getGarantierisques,
    getCategories,
    getBranches,
    getRisques,
    getEnergies,
    getCompagnies,
    getQualites,
    getOffres,
    getOffresVoyages,
    getOffresSante,
    getOffredetails,
    getMarques,
    getSystemesecurites,
    getModeles,
    getUsages,
    // AUTO 
    getTypeVehicule,
    getGenreVehicule,
    getProfession,
    getTypeSouscripteur,
    getTypeAssure,
    // IA
    getProfessionIA,
    getPays,
    getPaysZone,
    getCategoriePermis,
    getQualitesSouscripteur,
    // SANTE 
    getColleges,
    getZoneCouvertureSante,
    //CarteBrume
    // getCarteBrume
}

export default contratService
