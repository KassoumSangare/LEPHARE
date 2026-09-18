import {
    createSlice,
    createAsyncThunk
} from '@reduxjs/toolkit'
import correctionDevisService from './correctionDevisService'

const initialState = {
    corrections: [],
    devis: null, // Nouvel état pour stocker le devis
    isError: false,
    isSuccess: false,
    isLoading: false,
    message: ''
}

export const correctionDevis = createAsyncThunk(
    'corrections/create',
    async (correctionData, thunkAPI) => {
        try {
            const token = thunkAPI.getState().auth.token
            return await correctionDevisService.correctionDevis(correctionData, token)
        } catch (error) {
            console.error("❌ Erreur détaillée dans correctionDevis:", error);
            console.error("❌ Response data:", error.response && error.response.data);
            console.error("❌ Response status:", error.response && error.response.status);
            console.error("❌ Response headers:", error.response && error.response.headers);

            let errorMessage = error.message || 'Erreur inconnue';
            let errorDetails = null;

            if (error.response && error.response.data) {
                errorDetails = error.response.data;
                if (typeof error.response.data === 'object') {
                    // Si c'est un objet, essayer de récupérer le message ou les erreurs de validation
                    if (error.response.data.message) {
                        errorMessage = error.response.data.message;
                    } else if (error.response.data.error) {
                        errorMessage = error.response.data.error;
                    } else if (error.response.data.detail) {
                        errorMessage = error.response.data.detail;
                    } else {
                        // Afficher les erreurs de validation si disponibles
                        const validationErrors = Object.entries(error.response.data)
                            .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
                            .join('; ');
                        if (validationErrors) {
                            errorMessage = `Erreurs de validation: ${validationErrors}`;
                        }
                    }
                } else {
                    errorMessage = error.response.data;
                }
            }

            return thunkAPI.rejectWithValue({
                message: errorMessage,
                details: errorDetails,
                status: error.response && error.response.status,
                data: error.response && error.response.data
            })
        }
    }
)

export const enregistrerDevis = createAsyncThunk(
    'devis/enregistrer',
    async (devisData, thunkAPI) => {
        try {
            const token = thunkAPI.getState().auth.token
            const response = await correctionDevisService.enregistrerDevis(devisData, token)
            return response // Doit retourner un objet avec IdDevis
        } catch (error) {
            const message = (error.response && error.response.data && error.response.data.message) || error.message || error.toString()
            return thunkAPI.rejectWithValue(message)
        }
    }
)

export const correctionDevisSlice = createSlice({
    name: 'corrections',
    initialState,
    reducers: {
        reset: (state) => {
            state.isLoading = false
            state.isSuccess = false
            state.isError = false
            state.message = ''
        }
    },
    extraReducers: (builder) => {
        builder
            .addCase(correctionDevis.pending, (state) => {
                state.isLoading = true
            })
            .addCase(correctionDevis.fulfilled, (state, action) => {
                state.isLoading = false
                state.isSuccess = true
                state.corrections.push(action.payload)
            })
            .addCase(correctionDevis.rejected, (state, action) => {
                state.isLoading = false
                state.isError = true
                state.message = action.payload
            })
            .addCase(enregistrerDevis.pending, (state) => {
                state.isLoading = true
            })
            .addCase(enregistrerDevis.fulfilled, (state, action) => {
                state.isLoading = false
                state.isSuccess = true
                state.devis = action.payload // Met à jour avec la réponse contenant IdDevis
            })
            .addCase(enregistrerDevis.rejected, (state, action) => {
                state.isLoading = false
                state.isError = true
                state.message = action.payload
            })
    }
})

export const {
    reset
} = correctionDevisSlice.actions
export default correctionDevisSlice.reducer