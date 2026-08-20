import { replaceIoneBrandNames, replaceIoneBrandNamesInResource } from '../text'

describe('I-ONE brand text', () => {
  it('replaces upstream product and company names', () => {
    expect(replaceIoneBrandNames('Sign in to Dify — LangGenius, Inc.')).toBe(
      'Sign in to I-ONE — I-ONE',
    )
  })

  it('preserves compatibility identifiers and external addresses', () => {
    expect(
      replaceIoneBrandNames(
        'Send X-Dify-SSO-Token to https://docs.dify.ai and support@dify.ai for Dify.',
      ),
    ).toBe('Send X-Dify-SSO-Token to https://docs.dify.ai and support@dify.ai for I-ONE.')
  })

  it('replaces names recursively without mutating the source resource', () => {
    const source = {
      title: 'Dify Console',
      nested: { description: 'Built by LangGenius' },
      list: ['Dify Cloud'],
    }

    expect(replaceIoneBrandNamesInResource(source)).toEqual({
      title: 'I-ONE Console',
      nested: { description: 'Built by I-ONE' },
      list: ['I-ONE Cloud'],
    })
    expect(source.title).toBe('Dify Console')
  })
})
