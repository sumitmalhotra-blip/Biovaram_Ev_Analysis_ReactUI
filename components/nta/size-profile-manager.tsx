"use client"

import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import {
  NTA_LOCKED_QUALITY_PROFILE_ID,
  type NTASizeBin,
  useAnalysisStore,
} from "@/lib/store"
import { Lock, Plus, Save, Trash2 } from "lucide-react"

function cloneBins(bins: NTASizeBin[]): NTASizeBin[] {
  return bins.map((b) => ({ ...b }))
}

function isValidBins(bins: NTASizeBin[]): { ok: boolean; message?: string } {
  if (bins.length === 0) {
    return { ok: false, message: "At least one bin is required." }
  }

  const sorted = [...bins].sort((a, b) => a.min - b.min)
  for (let i = 0; i < sorted.length; i += 1) {
    const b = sorted[i]
    if (!Number.isFinite(b.min) || !Number.isFinite(b.max) || b.min >= b.max) {
      return { ok: false, message: `Invalid range for bin '${b.name}'.` }
    }
    if (i > 0) {
      const prev = sorted[i - 1]
      if (b.min < prev.max) {
        return { ok: false, message: `Bins '${prev.name}' and '${b.name}' overlap.` }
      }
    }
  }

  return { ok: true }
}

export function NTASizeProfileManager() {
  const { toast } = useToast()

  const {
    ntaSizeProfiles,
    selectedNTAAnalysisProfileId,
    ntaLockedBuckets,
    setSelectedNTAAnalysisProfileId,
    updateNTASizeProfile,
    setNTALockedBuckets,
  } = useAnalysisStore()

  const qualityProfile = useMemo(
    () => ntaSizeProfiles.find((p) => p.id === NTA_LOCKED_QUALITY_PROFILE_ID),
    [ntaSizeProfiles]
  )

  const selectedAnalysisProfile = useMemo(
    () => ntaSizeProfiles.find((p) => p.id === selectedNTAAnalysisProfileId),
    [ntaSizeProfiles, selectedNTAAnalysisProfileId]
  )

  const [draftName, setDraftName] = useState("")
  const [draftBins, setDraftBins] = useState<NTASizeBin[]>([])

  useEffect(() => {
    if (!selectedAnalysisProfile) return
    setDraftName(selectedAnalysisProfile.name)
    setDraftBins(cloneBins(selectedAnalysisProfile.bins))
  }, [selectedAnalysisProfile])

  const isLockedDraft = selectedAnalysisProfile?.locked

  const handleBinChange = (idx: number, patch: Partial<NTASizeBin>) => {
    setDraftBins((prev) => prev.map((b, i) => (i === idx ? { ...b, ...patch } : b)))
  }

  const handleAddBin = () => {
    const last = draftBins[draftBins.length - 1]
    const nextMin = last ? Math.round(last.max) : 50
    const nextMax = nextMin + 50
    setDraftBins((prev) => [
      ...prev,
      {
        id: `bin-${crypto.randomUUID()}`,
        name: `${nextMin}-${nextMax} nm`,
        min: nextMin,
        max: nextMax,
      },
    ])
  }

  const handleSaveProfile = () => {
    if (!selectedAnalysisProfile) return
    if (selectedAnalysisProfile.locked) {
      toast({
        title: "Profile is locked",
        description: "Locked quality profile cannot be modified.",
        variant: "destructive",
      })
      return
    }

    const validation = isValidBins(draftBins)
    if (!validation.ok) {
      toast({ title: "Invalid bins", description: validation.message, variant: "destructive" })
      return
    }

    updateNTASizeProfile(selectedAnalysisProfile.id, {
      name: draftName.trim() || selectedAnalysisProfile.name,
      bins: cloneBins(draftBins),
    })

    toast({
      title: "Profile saved",
      description: "Analysis profile updated successfully.",
    })
  }

  const handleLockCurrent = () => {
    const validation = isValidBins(draftBins)
    if (!validation.ok) {
      toast({ title: "Invalid bins", description: validation.message, variant: "destructive" })
      return
    }
    setNTALockedBuckets(cloneBins(draftBins))
    toast({ title: "Buckets locked", description: "Current bucket ranges are saved for side-by-side comparison." })
  }

  const handleClearLocked = () => {
    setNTALockedBuckets(null)
    toast({ title: "Locked buckets cleared", description: "Comparison snapshot removed." })
  }

  return (
    <Card className="card-3d">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Size Bucket Ranges</CardTitle>
        <CardDescription>
          Simple mode: edit current buckets, then lock current buckets to compare old vs new side-by-side.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border p-3 bg-secondary/20">
          <div className="flex items-center gap-2 mb-2">
            <Lock className="h-4 w-4 text-amber-500" />
            <p className="text-sm font-medium">Quality Profile (Locked)</p>
            <Badge variant="outline">Immutable</Badge>
          </div>
          <p className="text-xs text-muted-foreground mb-2">
            Quality checks always use this fixed profile to keep verdicts consistent.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {qualityProfile?.bins.map((b) => (
              <Badge key={b.id} variant="secondary" className="text-xs">
                {b.name}
              </Badge>
            ))}
          </div>
        </div>

        <div className="space-y-1.5">
          <Label>Current Bucket Set</Label>
          <Select value={selectedNTAAnalysisProfileId} onValueChange={setSelectedNTAAnalysisProfileId}>
            <SelectTrigger>
              <SelectValue placeholder="Current bucket set" />
            </SelectTrigger>
            <SelectContent>
              {ntaSizeProfiles
                .filter((profile) => profile.id !== NTA_LOCKED_QUALITY_PROFILE_ID)
                .map((profile) => (
                  <SelectItem key={profile.id} value={profile.id}>
                    {profile.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2 rounded-lg border p-3">
          <div className="space-y-1.5">
            <Label>Profile Name</Label>
            <Input
              value={draftName}
              onChange={(e) => setDraftName(e.target.value)}
              disabled={!!isLockedDraft}
              placeholder="Profile name"
            />
          </div>

          <div className="space-y-2">
            <Label>Bins</Label>
            {draftBins.map((bin, idx) => (
              <div key={bin.id} className="grid grid-cols-12 gap-2">
                <Input
                  className="col-span-5"
                  value={bin.name}
                  disabled={!!isLockedDraft}
                  onChange={(e) => handleBinChange(idx, { name: e.target.value })}
                  placeholder="Bin label"
                />
                <Input
                  className="col-span-3"
                  type="number"
                  disabled={!!isLockedDraft}
                  value={bin.min}
                  onChange={(e) => handleBinChange(idx, { min: Number(e.target.value) })}
                  placeholder="Min"
                />
                <Input
                  className="col-span-3"
                  type="number"
                  disabled={!!isLockedDraft}
                  value={bin.max}
                  onChange={(e) => handleBinChange(idx, { max: Number(e.target.value) })}
                  placeholder="Max"
                />
                <Button
                  className="col-span-1"
                  variant="ghost"
                  size="icon"
                  disabled={!!isLockedDraft || draftBins.length <= 1}
                  onClick={() => setDraftBins((prev) => prev.filter((_, i) => i !== idx))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" className="gap-1.5" onClick={handleAddBin} disabled={!!isLockedDraft}>
              <Plus className="h-4 w-4" />
              Add Bin
            </Button>
            <Button size="sm" className="gap-1.5" onClick={handleSaveProfile} disabled={!!isLockedDraft}>
              <Save className="h-4 w-4" />
              Save Current Profile
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5" onClick={handleLockCurrent}>
              <Lock className="h-4 w-4" />
              Lock Current Buckets
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5" onClick={handleClearLocked} disabled={!ntaLockedBuckets}>
              <Trash2 className="h-4 w-4" />
              Clear Locked
            </Button>
          </div>

          {ntaLockedBuckets && (
            <p className="text-xs text-muted-foreground">
              Locked snapshot active with {ntaLockedBuckets.length} bucket(s). Results page will show side-by-side comparison.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
