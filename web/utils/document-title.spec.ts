import { formatDocumentTitle, getApplicationTitle } from './document-title'

const mockIsIoneBrandedUi = vi.hoisted(() => vi.fn(() => false))

vi.mock('@/features/ione-branding/feature-flag', () => ({
  isIoneBrandedUi: () => mockIsIoneBrandedUi(),
}))

describe('document title', () => {
  beforeEach(() => {
    mockIsIoneBrandedUi.mockReturnValue(false)
  })

  it('preserves the upstream title when I-ONE branding is disabled', () => {
    expect(getApplicationTitle({ enabled: false, application_title: '' })).toBe('Dify')
  })

  it('uses I-ONE as the default application title in branded mode', () => {
    mockIsIoneBrandedUi.mockReturnValue(true)

    expect(getApplicationTitle({ enabled: false, application_title: '' })).toBe('I-ONE')
    expect(
      formatDocumentTitle(
        'Settings',
        getApplicationTitle({ enabled: false, application_title: '' }),
      ),
    ).toBe('Settings - I-ONE')
  })

  it('keeps an explicitly configured application title', () => {
    mockIsIoneBrandedUi.mockReturnValue(true)

    expect(getApplicationTitle({ enabled: true, application_title: 'Customer Portal' })).toBe(
      'Customer Portal',
    )
  })
})
