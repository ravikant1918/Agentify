import React from 'react'
import { cn } from '../utils'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  icon?: React.ReactNode
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  icon,
  className,
  id,
  ...props
}) => {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
            {icon}
          </div>
        )}
        <input
          id={inputId}
          className={cn(
            'block w-full px-3 py-2 border rounded-lg placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200',
            error
              ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
              : 'border-gray-300 dark:border-gray-600',
            'dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500',
            icon ? 'pl-10' : '',
            className
          )}
          {...props}
        />
      </div>
      {error && (
        <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
      {helperText && !error && (
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{helperText}</p>
      )}
    </div>
  )
}