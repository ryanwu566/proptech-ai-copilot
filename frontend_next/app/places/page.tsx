import { PlacesManager } from "@/components/places/places-manager";
import { placesCopy } from "@/lib/my-places-copy";
export default function MyPlacesPage() { return <PlacesManager catalogue={placesCopy} />; }
