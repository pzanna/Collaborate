import React from "react"

interface SelectProps {
  value: string
  onValueChange: (value: string) => void
  children: React.ReactNode
}

interface SelectTriggerProps {
  className?: string
  children: React.ReactNode
}

interface SelectContentProps {
  children: React.ReactNode
}

interface SelectItemProps {
  value: string
  children: React.ReactNode
}

interface SelectValueProps {
  placeholder?: string
}

export const Select: React.FC<SelectProps> = ({
  value,
  onValueChange,
  children,
}) => {
  return (
    <div className="relative">
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child) && child.type === SelectTrigger) {
          return React.cloneElement(child as React.ReactElement<any>, {
            value,
            onValueChange,
          })
        }
        return child
      })}
    </div>
  )
}

export const SelectTrigger: React.FC<
  SelectTriggerProps & {
    value?: string
    onValueChange?: (value: string) => void
  }
> = ({ className = "", children, value, onValueChange }) => {
  const [isOpen, setIsOpen] = React.useState(false)

  return (
    <div className="relative">
      <button
        type="button"
        className={`flex h-10 w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        {children}
        <svg
          className="h-4 w-4 opacity-50"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen &&
        React.Children.map(children, (child) => {
          if (React.isValidElement(child) && child.type === SelectContent) {
            return React.cloneElement(child as React.ReactElement<any>, {
              onSelect: (selectedValue: string) => {
                onValueChange?.(selectedValue)
                setIsOpen(false)
              },
            })
          }
          return null
        })}
    </div>
  )
}

export const SelectContent: React.FC<
  SelectContentProps & { onSelect?: (value: string) => void }
> = ({ children, onSelect }) => {
  return (
    <div className="absolute top-full left-0 z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg">
      <div className="py-1 max-h-60 overflow-auto">
        {React.Children.map(children, (child) => {
          if (React.isValidElement(child) && child.type === SelectItem) {
            return React.cloneElement(child as React.ReactElement<any>, {
              onSelect,
            })
          }
          return child
        })}
      </div>
    </div>
  )
}

export const SelectItem: React.FC<
  SelectItemProps & { onSelect?: (value: string) => void }
> = ({ value, children, onSelect }) => {
  return (
    <button
      type="button"
      className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 focus:bg-gray-100 focus:outline-none"
      onClick={() => onSelect?.(value)}
    >
      {children}
    </button>
  )
}

export const SelectValue: React.FC<SelectValueProps> = ({ placeholder }) => {
  return <span className="text-gray-500">{placeholder}</span>
}
