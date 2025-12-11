"use client"

import { useState } from "react"
import { useAnalysisStore } from "@/lib/store"
import { useApi } from "@/hooks/use-api"
import { PinnedCharts } from "./pinned-charts"
import { QuickStats } from "./quick-stats"
import { RecentActivity } from "./recent-activity"
import { QuickUpload } from "./quick-upload"
import { SampleDetailsModal } from "@/components/sample-details-modal"
import { DeleteConfirmationDialog } from "@/components/delete-confirmation-dialog"

export function DashboardTab() {
  const { pinnedCharts } = useAnalysisStore()
  const { getSample, getFCSResults, getNTAResults, deleteSample } = useApi()
  
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [sampleToDelete, setSampleToDelete] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

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

  return (
    <>
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-4 md:gap-6 p-4 md:p-6">
        <div className="space-y-4 md:space-y-6 min-w-0">
          {pinnedCharts.length > 0 && <PinnedCharts charts={pinnedCharts} />}
          <QuickStats />
          <RecentActivity 
            onViewSample={handleViewSample}
            onDeleteSample={handleDeleteClick}
          />
        </div>
        <div className="space-y-4 md:space-y-6">
          <QuickUpload />
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
