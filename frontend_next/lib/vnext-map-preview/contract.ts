export type SpatialObservationStatus =
  | "present"
  | "unknown"
  | "unavailable"
  | "partial_coverage"
  | "stale"
  | "no_match";

export type SpatialAuthority = "synthetic";

export type ParcelRelationship = "candidate" | "confirmed_working_geometry";

export type MapPoint = readonly [x: number, y: number];

export interface PropertyEntityViewModel {
  readonly propertyEntityId: string;
  readonly displayLabel: string;
  readonly locationSummary: string;
  readonly identityStatus: "reviewed";
}

export interface CaseContextViewModel {
  readonly workspaceId: string;
  readonly caseId: string;
  readonly caseTitle: string;
  readonly purpose: string;
  readonly reviewStage: string;
  readonly reviewOwner: string;
  readonly selectedPropertyEntity: PropertyEntityViewModel | null;
}

export interface ParcelFeatureViewModel {
  readonly geometryId: string;
  readonly parcelIdentityReferenceId: string;
  readonly layerKey: "parcel_candidates" | "confirmed_parcel";
  readonly label: string;
  readonly relationship: ParcelRelationship;
  readonly matchBasis: string;
  readonly areaLabel: string;
  readonly confidenceLabel?: string;
  readonly evidenceId: string;
  readonly sourceLabel: string;
  readonly authority: SpatialAuthority;
  readonly polygon: readonly MapPoint[];
}

export interface MapLayerViewModel {
  readonly key: string;
  readonly title: string;
  readonly category: "parcel" | "planning" | "environment" | "access" | "reference";
  readonly status: SpatialObservationStatus;
  readonly selectedByDefault: boolean;
  readonly sourceLabel: string;
  readonly authority: SpatialAuthority;
  readonly attribution: string;
  readonly evidenceId: string;
  readonly observedAt: string;
  readonly coverageLabel: string;
  readonly summary: string;
  readonly limitation: string;
  readonly color: string;
  readonly lineStyle: "solid" | "dashed" | "dotted";
}

export interface MapLegendItemViewModel {
  readonly layerKey: string;
  readonly title: string;
  readonly authority: SpatialAuthority;
  readonly observationStatus: SpatialObservationStatus;
  readonly attribution: string;
  readonly color: string;
  readonly lineStyle: "solid" | "dashed" | "dotted";
}

export interface MapViewportViewModel {
  readonly centerLongitude: number;
  readonly centerLatitude: number;
  readonly zoom: number;
  readonly bounds: readonly [west: number, south: number, east: number, north: number];
}

export interface MapFeatureSelectionViewModel {
  readonly featureId: string;
  readonly featureType: "candidate_parcel" | "confirmed_parcel";
  readonly layerKey: string;
  readonly evidenceId: string;
}

export interface MapWorkspaceViewModel {
  readonly context: CaseContextViewModel;
  readonly candidateParcels: readonly ParcelFeatureViewModel[];
  readonly confirmedParcels: readonly ParcelFeatureViewModel[];
  readonly layers: readonly MapLayerViewModel[];
  readonly observationIds: readonly string[];
  readonly viewport: MapViewportViewModel;
  readonly limitations: readonly string[];
}

export function legendForLayers(layers: readonly MapLayerViewModel[]): MapLegendItemViewModel[] {
  return layers.map((layer) => ({
    layerKey: layer.key,
    title: layer.title,
    authority: layer.authority,
    observationStatus: layer.status,
    attribution: layer.attribution,
    color: layer.color,
    lineStyle: layer.lineStyle,
  }));
}
