import axios from 'axios'

const correctionDevis = async (correctionData, token) => {
    const config = {
        headers: {
            Authorization: `Token ${token}`,
        }
    }

    const response = await axios.post(
        process.env.REACT_APP_API_URL + 'correctiondevis/',
        correctionData,
        config
    )
    return response.data
}

const correctionDevisService = {
    correctionDevis
}

export default correctionDevisService