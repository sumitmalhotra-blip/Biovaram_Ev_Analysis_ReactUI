"use client"

import { useState } from "react"
import { RotateCcw } from "lucide-react"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"
import { PinnedCharts } from "./pinned-charts"
import { QuickStats } from "./quick-stats"
import { RecentActivity } from "./recent-activity"
import { QuickUpload } from "./quick-upload"
import { DashboardAIChat } from "./dashboard-ai-chat"
import { SavedImagesGallery } from "./saved-images-gallery"
import { SampleDetailsModal } from "@/components/sample-details-modal"
import { DeleteConfirmationDialog } from "@/components/delete-confirmation-dialog"

export function DashboardTab() {
  const { pinnedCharts, clearPinnedCharts, clearChatMessages } = useAnalysisStore()
  const { getSample, getFCSResults, getNTAResults, deleteSample } = useApi()
  const { toast } = useToast()
  
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [sampleToDelete, setSampleToDelete] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isChatMinimized, setIsChatMinimized] = useState(false)

  const handleViewSample = (sampleId: string) => {
    setSelectedSampleId(sampleId)
    setShowDetailsModal(true)
  }

  const handleDeleteClick = (sampleId: string) => {
    setSampleToDelete(sampleId)
    setShowDeleteDialog(true)
  }

  const handleConfirmDelete = async () => {
    if (!sampleToDelete) return

    setIsDeleting(true)
    try {
      await deleteSample(sampleToDelete)
      setShowDeleteDialog(false)
      setSampleToDelete(null)
    } finally {
      setIsDeleting(false)
    }
  }

  const handleResetTab = () => {
    clearPinnedCharts()
    clearChatMessages()
    setSelectedSampleId(null)
    setShowDetailsModal(false)
    setShowDeleteDialog(false)
    setSampleToDelete(null)
    setIsChatMinimized(false)
    toast({
      title: "Dashboard Reset",
      description: "All pinned charts and chat messages have been cleared.",
    })
  }

  return (
    <>
      <div className="p-4 md:p-6">
        {/* Header with Reset Button */}
        <div className="flex items-center justify-between mb-4 md:mb-6">
          <div>
            <h2 className="text-2xl font-bold">Dashboard</h2>
            <p className="text-sm text-muted-foreground">Overview of your EV analysis workspace</p>
          </div>
          <Button variant="outline" size="sm" onClick={handleResetTab} className="gap-2">
            <RotateCcw className="h-4 w-4" />
            Reset Tab
          </Button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-4 md:gap-6">
          <div className="space-y-4 md:space-y-6 min-w-0">
            {pinnedCharts.length > 0 && <PinnedCharts charts={pinnedCharts} />}
            <QuickStats />
            <RecentActivity 
              onViewSample={handleViewSample}
              onDeleteSample={handleDeleteClick}
            />
            
            {/* AI Chat Assistant */}
            <DashboardAIChat 
              isMinimized={isChatMinimized}
              onMinimize={() => setIsChatMinimized(!isChatMinimized)}
            />
          </div>
          <div className="space-y-4 md:space-y-6">
            <QuickUpload />
            <SavedImagesGallery maxHeight="400px" />
          </div>
        </div>
      </div>

      {/* Sample Details Modal */}
      <SampleDetailsModal
        open={showDetailsModal}
        onOpenChange={setShowDetailsModal}
        sampleId={selectedSampleId}
        onFetchSample={getSample}
        onFetchFCSResults={getFCSResults}
        onFetchNTAResults={getNTAResults}
        onDelete={handleDeleteClick}
      />

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        sampleId={sampleToDelete}
        onConfirm={handleConfirmDelete}
        isDeleting={isDeleting}
      />
    </>
  )
}
