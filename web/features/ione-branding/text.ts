import type { ResourceKey } from 'i18next'

const protectedBrandReferences = /(https?:\/\/[^\s<>"')]+|[\w.+-]+@dify\.ai|X-Dify-[a-z0-9-]+)/gi

export const replaceIoneBrandNames = (text: string) => {
  const protectedValues: string[] = []
  const protectedText = text.replace(protectedBrandReferences, (value) => {
    const placeholder = `__IONE_BRAND_PROTECTED_${protectedValues.length}__`
    protectedValues.push(value)
    return placeholder
  })

  const brandedText = protectedText
    .replace(/LangGenius(?:, Inc\.)?/g, 'I-ONE')
    .replace(/\bDify\b/g, 'I-ONE')

  return brandedText.replace(/__IONE_BRAND_PROTECTED_(\d+)__/g, (_, index: string) => {
    return protectedValues[Number(index)] ?? ''
  })
}

export const replaceIoneBrandNamesInResource = (resource: ResourceKey): ResourceKey => {
  if (typeof resource === 'string') return replaceIoneBrandNames(resource)
  if (Array.isArray(resource)) return resource.map(replaceIoneBrandNamesInResource)

  return Object.fromEntries(
    Object.entries(resource).map(([key, value]) => [
      key,
      replaceIoneBrandNamesInResource(value as ResourceKey),
    ]),
  )
}
