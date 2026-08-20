'use client'
import { cn } from '@langgenius/dify-ui/cn'
import { useSuspenseQuery } from '@tanstack/react-query'
import * as React from 'react'
import ChangePasswordForm from '@/app/forgot-password/ChangePasswordForm'
import { ProductCopyright } from '@/features/ione-branding/copyright'
import { systemFeaturesQueryOptions } from '@/features/system-features/client'
import { useSearchParams } from '@/next/navigation'
import Header from '../signin/_header'
import ForgotPasswordForm from './ForgotPasswordForm'

const ForgotPassword = () => {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')
  const { data: systemFeatures } = useSuspenseQuery(systemFeaturesQueryOptions())

  return (
    <div className={cn('flex min-h-screen w-full justify-center bg-background-default-burn p-6')}>
      <div
        className={cn(
          'flex w-full shrink-0 flex-col rounded-2xl border border-effects-highlight bg-background-default-subtle',
        )}
      >
        <Header />
        {token ? <ChangePasswordForm /> : <ForgotPasswordForm />}
        {!systemFeatures.branding.enabled && (
          <ProductCopyright className="px-8 py-6 text-sm font-normal text-text-tertiary" />
        )}
      </div>
    </div>
  )
}

export default ForgotPassword
