import React, { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardContent } from "../ui/card"
import {
  ClockIcon,
  ChatBubbleLeftRightIcon,
  ClipboardDocumentListIcon,
} from "@heroicons/react/24/outline"
import { useAuth } from "../../hooks/useAuth"
import { ROUTES } from "../../utils/routes"

interface PendingItem {
  id: string
  title: string
  type: "task" | "project" | "topic"
  status: string
  created_at: string
}

const academicQuotes = [
  "The important thing is not to stop questioning. - Albert Einstein",
  "Research is what I'm doing when I don't know what I'm doing. - Wernher von Braun",
  "The only true wisdom is in knowing you know nothing. - Socrates",
  "If I have seen further it is by standing on the shoulders of Giants. - Isaac Newton",
  "Science is a way of thinking much more than it is a body of knowledge. - Carl Sagan",
  "The good thing about science is that it's true whether or not you believe in it. - Neil deGrasse Tyson",
  "Research is formalized curiosity. It is poking and prying with a purpose. - Zora Neale Hurston",
  "The whole of science is nothing more than a refinement of everyday thinking. - Albert Einstein",
  "In science there is only physics; all the rest is stamp collecting. - Ernest Rutherford",
  "The most exciting phrase to hear in science is not 'Eureka!' but 'That's funny...' - Isaac Asimov",
]

const WelcomePage: React.FC = () => {
  const [greeting, setGreeting] = useState("")
  const [quote, setQuote] = useState("")
  const [pendingItems, setPendingItems] = useState<PendingItem[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  // Get the logged-in user's information
  const { user } = useAuth()

  // Use the user's first name, with fallback to "Researcher" if not available
  const firstName = user?.first_name || "Researcher"

  // Generate time-based greeting
  useEffect(() => {
    const hour = new Date().getHours()
    if (hour < 12) {
      setGreeting(`Good Morning ${firstName}`)
    } else if (hour < 17) {
      setGreeting(`Good Afternoon ${firstName}`)
    } else {
      setGreeting(`Good Evening ${firstName}`)
    }
  }, [firstName])

  // Generate random academic quote
  useEffect(() => {
    const randomIndex = Math.floor(Math.random() * academicQuotes.length)
    setQuote(academicQuotes[randomIndex])
  }, [])

  // Load pending items (using mock data)
  useEffect(() => {
    const loadPendingItems = async () => {
      // Simulate loading delay for better UX
      await new Promise((resolve) => setTimeout(resolve, 500))

      // Use mock data for pending items
      const mockPendingItems: PendingItem[] = [
        {
          id: "1",
          title: "Complete literature review for AI research project",
          type: "task",
          status: "pending",
          created_at: new Date().toISOString(),
        },
        {
          id: "2",
          title: "Review draft for Neural Networks topic",
          type: "topic",
          status: "active",
          created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: "3",
          title: "Machine Learning Research Project",
          type: "project",
          status: "active",
          created_at: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
        },
      ]
      setPendingItems(mockPendingItems)
      setLoading(false)
    }

    loadPendingItems()
  }, [])

  const getItemTypeIcon = (type: string) => {
    switch (type) {
      case "task":
        return <ClipboardDocumentListIcon className="h-4 w-4" />
      case "project":
        return <ClockIcon className="h-4 w-4" />
      case "topic":
        return <ChatBubbleLeftRightIcon className="h-4 w-4" />
      default:
        return <ClipboardDocumentListIcon className="h-4 w-4" />
    }
  }

  const getItemTypeColor = (type: string) => {
    switch (type) {
      case "task":
        return "text-blue-600 bg-blue-50"
      case "project":
        return "text-green-600 bg-green-50"
      case "topic":
        return "text-purple-600 bg-purple-50"
      default:
        return "text-gray-600 bg-gray-50"
    }
  }

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60)
    )

    if (diffInHours < 1) return "Less than an hour ago"
    if (diffInHours < 24)
      return `${diffInHours} hour${diffInHours > 1 ? "s" : ""} ago`

    const diffInDays = Math.floor(diffInHours / 24)
    return `${diffInDays} day${diffInDays > 1 ? "s" : ""} ago`
  }

  return (
    <div className="p-8 space-y-8">
      {/* Welcome Header */}
      <div className="text-center py-8">
        <div className="flex justify-center mb-4"></div>
        <h1 className="text-4xl font-bold text-foreground mb-1">{greeting}!</h1>
        <p className="text-lg text-muted-foreground mb-4">
          Welcome back to your research workspace
        </p>
        {/* Academic Quote */}
        <p className="text-sm italic text-muted-foreground">"{quote}"</p>
      </div>

      {/* Pending Items */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ClipboardDocumentListIcon className="h-5 w-5" />
            Pending Items
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : pendingItems.length > 0 ? (
            <div className="space-y-3">
              {pendingItems.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2 rounded-full ${getItemTypeColor(
                        item.type
                      )}`}
                    >
                      {getItemTypeIcon(item.type)}
                    </div>
                    <div>
                      <p className="font-medium text-foreground">
                        {item.title}
                      </p>
                      <p className="text-sm text-muted-foreground capitalize">
                        {item.type} • {item.status}
                      </p>
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {formatTimeAgo(item.created_at)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <ClipboardDocumentListIcon className="h-12 w-12 mx-auto mb-3 text-muted-foreground/50" />
              <p>No pending items at the moment</p>
              <p className="text-sm">All caught up! Great work.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="cursor-pointer hover:shadow-md transition-shadow">
          <CardContent className="text-center py-6">
            <ClockIcon className="h-8 w-8 mx-auto mb-2 text-primary" />
            <h3 className="font-semibold text-foreground">Start Research</h3>
            <p className="text-sm text-muted-foreground">
              Begin a new research session
            </p>
          </CardContent>
        </Card>

        <Card 
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate('/test-projects')}
        >
          <CardContent className="text-center py-6">
            <ClipboardDocumentListIcon className="h-8 w-8 mx-auto mb-2 text-primary" />
            <h3 className="font-semibold text-foreground">View Projects</h3>
            <p className="text-sm text-muted-foreground">
              Browse your research projects
            </p>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow">
          <CardContent className="text-center py-6">
            <ChatBubbleLeftRightIcon className="h-8 w-8 mx-auto mb-2 text-primary" />
            <h3 className="font-semibold text-foreground">Review Tasks</h3>
            <p className="text-sm text-muted-foreground">
              Check task progress and results
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default WelcomePage
