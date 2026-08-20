import { isIoneBrandedUi } from './feature-flag'

export const DIFY_PRODUCT_NAME = 'Dify'
export const IONE_PRODUCT_NAME = 'I-ONE'

export const getProductName = () => (isIoneBrandedUi() ? IONE_PRODUCT_NAME : DIFY_PRODUCT_NAME)

export const getCopyrightOwner = () => (isIoneBrandedUi() ? IONE_PRODUCT_NAME : 'LangGenius, Inc.')
