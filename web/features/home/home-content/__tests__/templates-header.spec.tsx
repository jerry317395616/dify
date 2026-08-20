import { render, screen } from '@testing-library/react'
import { HomeTemplatesHeader } from '../templates-header'

const mockIsIoneBrandedUi = vi.hoisted(() => vi.fn(() => false))

vi.mock('@/features/ione-branding/feature-flag', () => ({
  isIoneBrandedUi: () => mockIsIoneBrandedUi(),
}))

vi.mock('@/app/components/explore/category', () => ({
  default: () => <div data-testid="category" />,
}))

vi.mock('@/app/components/base/search-input', () => ({
  SearchInput: () => <input aria-label="template search" />,
}))

const renderHeader = () =>
  render(
    <HomeTemplatesHeader
      allCategoriesEn="All"
      categories={['All']}
      currCategory="All"
      keywords=""
      onCategoryChange={vi.fn()}
      onKeywordsChange={vi.fn()}
    />,
  )

describe('HomeTemplatesHeader', () => {
  beforeEach(() => {
    mockIsIoneBrandedUi.mockReturnValue(false)
  })

  it('keeps the upstream template catalog link in the standard console', () => {
    renderHeader()

    expect(screen.getByRole('link', { name: 'explore.apps.viewMore' })).toHaveAttribute(
      'href',
      'https://marketplace.dify.ai/templates',
    )
  })

  it('hides the external template catalog link in the I-ONE console', () => {
    mockIsIoneBrandedUi.mockReturnValue(true)

    renderHeader()

    expect(screen.queryByRole('link', { name: 'explore.apps.viewMore' })).not.toBeInTheDocument()
  })
})
