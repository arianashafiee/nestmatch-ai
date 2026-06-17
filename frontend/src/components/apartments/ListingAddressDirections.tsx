import { AddressDirectionsMenu } from '@/components/apartments/AddressDirectionsMenu'
import { useStudentProfile } from '@/context/StudentProfileContext'
import type { Apartment } from '@/types/apartment'
import { mapLocationForApartment } from '@/types/apartment'

interface ListingAddressDirectionsProps {
  apartment: Apartment
  className?: string
  compact?: boolean
  onPointerDown?: (event: React.MouseEvent) => void
}

function listingAddress(apartment: Apartment): string {
  return (
    mapLocationForApartment(apartment) ||
    apartment.analysis?.location?.trim() ||
    ''
  )
}

function campusFromProfile(
  campusLocation: string,
  university: string,
): string {
  return campusLocation.trim() || university.trim()
}

export function ListingAddressDirections({
  apartment,
  className,
  compact,
  onPointerDown,
}: ListingAddressDirectionsProps) {
  const { profile } = useStudentProfile()
  const listing = listingAddress(apartment)
  const campus = campusFromProfile(profile.campusLocation, profile.university)

  return (
    <AddressDirectionsMenu
      address={listing}
      origin={campus}
      requireOrigin
      menuTitle="Directions from your campus"
      missingOriginMessage="Add your campus address in"
      className={className}
      compact={compact}
      onPointerDown={onPointerDown}
    />
  )
}
