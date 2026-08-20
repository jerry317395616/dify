import type { BrandingModel } from '@dify/contracts/api/console/system-features/types.gen'
import { getProductName } from '@/features/ione-branding/product'

export const getApplicationTitle = (
  branding?: Pick<BrandingModel, 'application_title' | 'enabled'>,
) =>
  branding?.enabled && branding.application_title ? branding.application_title : getProductName()

export const formatDocumentTitle = (title: string, applicationTitle: string) =>
  title ? `${title} - ${applicationTitle}` : applicationTitle
