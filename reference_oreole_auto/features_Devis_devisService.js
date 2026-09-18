import axios from 'axios'


// save new devis
const saveDevis = async (devisData, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'enregistrementdevis', devisData, config)

    return response.data
}

// ending new devis flotte 
const finalisationdevisauto = async (devisData, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'finalisationdevisauto', devisData, config)

    return response.data
}

// save new devis
const saveDevisIA = async (devisData, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'enregistrementdevisia', devisData, config)

    return response.data
}

// save new devis Voyage
const saveDevisVoyage = async (devisData, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'enregistrementdevisvoyage', devisData, config)

    return response.data
}

// save new devis mrh
const saveDevisMrh = async (devisData, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'enregistrementdevismrh', devisData, config)

    return response.data
}

// save new devis dommages
const saveDevisDommages = async (devisData, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'enregistrementdevistousrisquesinfo', devisData, config)

    return response.data
}

// save new devis sante
const saveDevisSante = async (devisData, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'enregistrementdevissante', devisData, config)

    return response.data
}

// get saved devis 
const getSavedDevis = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL, config)
    return response.data
}

// validate newDevis
const validateDevis = async (validationDetail, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'confirmationdevis', validationDetail, config)

    return response.data
}

// get validDevis 
const getValidDevis = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL, config)
    return response.data
}

// Delete the Devis
const deleteDevisService = async (deleteDevis, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'annulationsaisiedevis', deleteDevis, config)
    return response.data
}

// Delete the Devis Adhérént
const deleteAdherentService = async (deleteDevis, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'annulationsaisieadherent', deleteDevis, config)
    return response.data
}


// Delete the Devis Affiliés
const deleteAffilieService = async (deleteDevis, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + 'annulationsaisieaffilie', deleteDevis, config)
    return response.data
}


// getDevis 
const getDevis = async (token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + 'devis', config)
    return response.data
}

// getOneDevis 
const getOneDevis = async (token, iddevis) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + `devis/${iddevis}`, config)
    return response.data
}

// get Devis Infos 

const getDevisInfo = async (id, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`
        }
    }
    const response = await axios.get(process.env.REACT_APP_API_URL + `infodevis/${id}?page_size=100`, config)
    return response.data
}





/**
 * 
 * 
 */
// annulation de contrat
const annulationDevis = async (annulationDetail, token,) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }
    const response = await axios.post(process.env.REACT_APP_API_URL + `avenant/annulation`, annulationDetail, config)
    return response.data
}


const devisService = {
    deleteDevisService,
    deleteAdherentService,
    deleteAffilieService,
    getValidDevis,
    validateDevis,
    getSavedDevis,
    saveDevisDommages,
    saveDevis,
    getDevis,
    saveDevisSante,
    getOneDevis,
    saveDevisIA,
    saveDevisVoyage,
    saveDevisMrh,
    getDevisInfo,
    finalisationdevisauto,
    annulationDevis,

}

export default devisService