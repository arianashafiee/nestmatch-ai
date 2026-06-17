import { AddressDirectionsMenu } from '@/components/apartments/AddressDirectionsMenu'

interface TourAddressDirectionsProps {
  address: string
  className?: string
}

export function TourAddressDirections({
  address,
  className,
}: TourAddressDirectionsProps) {
  return (
    <AddressDirectionsMenu
      address={address}
      menuTitle="Directions from current location"
      className={className}
    />
  )
}
