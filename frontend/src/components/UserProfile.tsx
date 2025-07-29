import { useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/hooks/useAuth"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import {
  Camera,
  Save,
  Eye,
  EyeOff,
  Shield,
  ShieldCheck,
  ArrowLeft,
  User,
  CircleUserRound,
  Mail,
  Lock,
  Settings,
} from "lucide-react"
import { ROUTES } from "@/utils/routes"

export function UserProfile() {
  const navigate = useNavigate()
  const { user, refreshUserData } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Profile state
  const [firstName, setFirstName] = useState(user?.first_name || "")
  const [lastName, setLastName] = useState(user?.last_name || "")
  const [email, setEmail] = useState(user?.email || "")
  const [profileImage, setProfileImage] = useState<string>("")
  const [profileImageFile, setProfileImageFile] = useState<File | null>(null)

  // Password state
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Loading and error states
  const [isProfileLoading, setIsProfileLoading] = useState(false)
  const [isPasswordLoading, setIsPasswordLoading] = useState(false)
  const [profileError, setProfileError] = useState("")
  const [passwordError, setPasswordError] = useState("")
  const [profileSuccess, setProfileSuccess] = useState("")
  const [passwordSuccess, setPasswordSuccess] = useState("")

  const handleProfileImageClick = () => {
    fileInputRef.current?.click()
  }

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // Validate file type
      if (!file.type.startsWith("image/")) {
        setProfileError("Please select a valid image file")
        return
      }

      // Validate file size (5MB limit)
      if (file.size > 5 * 1024 * 1024) {
        setProfileError("Image size must be less than 5MB")
        return
      }

      // Create preview URL
      const imageUrl = URL.createObjectURL(file)
      setProfileImage(imageUrl)
      setProfileError("")

      // Store the actual file for upload
      setProfileImageFile(file)
    }
  }

  const handleProfilePictureUpload = async () => {
    if (!profileImageFile) return null

    try {
      const token = localStorage.getItem("access_token")
      const formData = new FormData()
      formData.append("file", profileImageFile)

      const response = await fetch(
        "http://localhost:8013/upload-profile-picture",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        }
      )

      const data = await response.json()

      if (response.ok) {
        return data.profile_image_url
      } else {
        throw new Error(data.detail || "Failed to upload profile picture")
      }
    } catch (error) {
      throw new Error("Network error. Please try again.")
    }
  }

  const handleProfileUpdate = async () => {
    if (!firstName.trim() || !lastName.trim() || !email.trim()) {
      setProfileError("All fields are required")
      return
    }

    if (!email.includes("@")) {
      setProfileError("Please enter a valid email address")
      return
    }

    setIsProfileLoading(true)
    setProfileError("")
    setProfileSuccess("")

    try {
      let uploadedImageUrl = null

      // Upload profile picture first if there's a new one
      if (profileImageFile) {
        uploadedImageUrl = await handleProfilePictureUpload()
      }

      const token = localStorage.getItem("access_token")

      // Prepare the request body for profile update
      const requestBody: any = {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
      }

      // Include the uploaded image URL if available
      if (uploadedImageUrl) {
        requestBody.profile_image_url = uploadedImageUrl
      }

      const response = await fetch("http://localhost:8013/users/me", {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      })

      const data = await response.json()

      if (response.ok) {
        setProfileSuccess("Profile updated successfully!")
        setProfileImageFile(null) // Clear the file after successful upload
        await refreshUserData()
      } else {
        setProfileError(data.detail || "Failed to update profile")
      }
    } catch (error) {
      setProfileError(
        error instanceof Error
          ? error.message
          : "Network error. Please try again."
      )
    } finally {
      setIsProfileLoading(false)
    }
  }

  const handlePasswordChange = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError("All password fields are required")
      return
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match")
      return
    }

    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters long")
      return
    }

    setIsPasswordLoading(true)
    setPasswordError("")
    setPasswordSuccess("")

    try {
      const token = localStorage.getItem("access_token")
      const response = await fetch("http://localhost:8013/change-password", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        setPasswordSuccess("Password changed successfully!")
        setCurrentPassword("")
        setNewPassword("")
        setConfirmPassword("")
      } else {
        setPasswordError(data.detail || "Failed to change password")
      }
    } catch (error) {
      setPasswordError("Network error. Please try again.")
    } finally {
      setIsPasswordLoading(false)
    }
  }

  const handle2FASetup = () => {
    navigate(ROUTES.TWO_FACTOR)
  }

  if (!user) {
    return <div>Loading...</div>
  }

  return (
    <div className="container max-w-6xl mx-auto py-8 px-4 space-y-6 relative">
      {/* Back to Dashboard Button will be at the bottom */}

      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold">Profile Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Information */}
        <div className="lg:col-span-2 space-y-6">
          {/* Personal Information */}
          <Card>
            <CardHeader className="text-center">
              <CardTitle className="flex items-center justify-center gap-2">
                <User className="h-5 w-5" />
                Personal Information
              </CardTitle>
              <CardDescription>
                Update your personal details and profile picture
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Profile Picture */}
              <div className="flex items-center gap-4">
                <div className="relative">
                  <Avatar className="h-20 w-20">
                    <AvatarImage
                      src={
                        profileImage ||
                        (user.profile_image_url
                          ? `http://localhost:8013${user.profile_image_url}`
                          : "/avatars/researcher.jpg")
                      }
                    />
                    <AvatarFallback className="text-lg">
                      {firstName[0]?.toUpperCase() || ""}
                      {lastName[0]?.toUpperCase() || ""}
                    </AvatarFallback>
                  </Avatar>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="absolute -bottom-2 -right-2 h-8 w-8 rounded-full p-0"
                    onClick={handleProfileImageClick}
                  >
                    <Camera className="h-4 w-4" />
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleImageChange}
                    className="hidden"
                  />
                </div>
                <div>
                  <p className="text-sm font-medium">Profile Picture</p>
                  <p className="text-xs text-muted-foreground">
                    Click the camera icon to upload a new image
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Max size: 5MB. Formats: JPG, PNG, GIF
                  </p>
                </div>
              </div>

              {/* Name Fields */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input
                    id="firstName"
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="Enter first name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input
                    id="lastName"
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="Enter last name"
                  />
                </div>
              </div>

              {/* Email Field */}
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <div className="relative">
                  <Mail className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter email address"
                    className="pl-10"
                  />
                </div>
              </div>

              {/* Profile Messages */}
              {profileError && (
                <div className="text-sm text-red-500 bg-red-50 p-3 rounded-md">
                  {profileError}
                </div>
              )}
              {profileSuccess && (
                <div className="text-sm text-green-500 bg-green-50 p-3 rounded-md">
                  {profileSuccess}
                </div>
              )}

              {/* Save Button */}
              <div className="flex justify-center">
                <Button
                  onClick={handleProfileUpdate}
                  disabled={isProfileLoading}
                  className="w-full md:w-auto"
                >
                  <Save className="h-4 w-4 mr-2" />
                  {isProfileLoading ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Change Password */}
          <Card>
            <CardHeader className="text-center">
              <CardTitle className="flex items-center justify-center gap-2">
                <Lock className="h-5 w-5" />
                Change Password
              </CardTitle>
              <CardDescription>
                Update your password to keep your account secure
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Current Password */}
              <div className="space-y-2">
                <Label htmlFor="currentPassword">Current Password</Label>
                <div className="relative">
                  <Input
                    id="currentPassword"
                    type={showCurrentPassword ? "text" : "password"}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter current password"
                    className="pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  >
                    {showCurrentPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              {/* New Password */}
              <div className="space-y-2">
                <Label htmlFor="newPassword">New Password</Label>
                <div className="relative">
                  <Input
                    id="newPassword"
                    type={showNewPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Enter new password"
                    className="pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                  >
                    {showNewPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Password must be at least 8 characters long
                </p>
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                <div className="relative">
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm new password"
                    className="pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              {/* Password Messages */}
              {passwordError && (
                <div className="text-sm text-red-500 bg-red-50 p-3 rounded-md">
                  {passwordError}
                </div>
              )}
              {passwordSuccess && (
                <div className="text-sm text-green-500 bg-green-50 p-3 rounded-md">
                  {passwordSuccess}
                </div>
              )}

              {/* Change Password Button */}
              <div className="flex justify-center">
                <Button
                  onClick={handlePasswordChange}
                  disabled={isPasswordLoading}
                  className="w-full md:w-auto"
                >
                  <Lock className="h-4 w-4 mr-2" />
                  {isPasswordLoading ? "Changing..." : "Change Password"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Security Settings Sidebar */}
        <div className="space-y-6">
          {/* 2FA Management */}
          <Card>
            <CardHeader className="text-center">
              <CardTitle className="flex items-center justify-center gap-2">
                {user.is_2fa_enabled ? (
                  <>
                    <ShieldCheck className="h-5 w-5 text-green-600" />
                    Two-Factor Authentication
                  </>
                ) : (
                  <>
                    <Shield className="h-5 w-5 text-orange-600" />
                    Two-Factor Authentication
                  </>
                )}
              </CardTitle>
              <CardDescription>
                Add an extra layer of security to your account
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Status</p>
                </div>
                <Badge variant={user.is_2fa_enabled ? "default" : "secondary"}>
                  {user.is_2fa_enabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>

              <Separator />

              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  {user.is_2fa_enabled
                    ? "Two-factor authentication is protecting your account. You can manage your 2FA settings."
                    : "Enable 2FA to secure your account with an authenticator app."}
                </p>

                <Button
                  onClick={handle2FASetup}
                  variant={user.is_2fa_enabled ? "outline" : "default"}
                  className="w-full"
                >
                  {user.is_2fa_enabled ? (
                    <>
                      <Settings className="h-4 w-4 mr-2" />
                      Manage 2FA
                    </>
                  ) : (
                    <>
                      <Shield className="h-4 w-4 mr-2" />
                      Setup 2FA
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Account Info */}
          <Card>
            <CardHeader className="text-center">
              <CardTitle className="flex items-center justify-center gap-2">
                <CircleUserRound className="h-5 w-5" />
                Account Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm font-medium">User ID</p>
                <p className="text-xs text-muted-foreground">#{user.id}</p>
              </div>
              <div>
                <p className="text-sm font-medium">Role</p>
                <Badge variant="outline" className="text-xs">
                  {user.role}
                </Badge>
              </div>
              <div>
                <p className="text-sm font-medium">Account Status</p>
                <Badge variant="default" className="text-xs">
                  Active
                </Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Back to Dashboard Button - Centered in Container */}
      <div className="flex justify-center pt-4">
        <Button variant="outline" onClick={() => navigate(ROUTES.WELCOME)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Button>
      </div>
    </div>
  )
}
