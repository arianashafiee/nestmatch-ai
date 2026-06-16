import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('NestMatch render error:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-svh items-center justify-center bg-slate-50 p-6">
          <div className="max-w-md rounded-xl border border-red-200 bg-white p-6 text-center shadow-sm">
            <h1 className="text-lg font-semibold text-slate-900">
              Something went wrong
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              {this.state.error.message}
            </p>
            <button
              type="button"
              onClick={() => {
                localStorage.removeItem('nestmatch-apartments')
                localStorage.removeItem('nestmatch-apartment-drafts')
                window.location.reload()
              }}
              className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Clear cache & reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
