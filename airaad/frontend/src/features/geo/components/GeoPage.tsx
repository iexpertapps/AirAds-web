import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, ChevronRight, ChevronDown, Globe, Building2, Map, Landmark, Save, Trash2 } from 'lucide-react';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { Button } from '@/shared/components/dls/Button';
import { Input } from '@/shared/components/dls/Input';
import { Select } from '@/shared/components/dls/Select';
import { Drawer } from '@/shared/components/dls/Drawer';
import { Modal } from '@/shared/components/dls/Modal';
import { SkeletonTable } from '@/shared/components/dls/SkeletonTable';
import { RoleGate } from '@/shared/components/RoleGate';
import { useToast } from '@/shared/hooks/useToast';
import type { GeoJSONPoint } from '@/shared/types/geo';
import { GPSInput } from '@/shared/components/dls/GPSInput';
import { GPSMap } from '@/shared/components/dls/GPSMap';
import { formatLabel } from '@/shared/utils/formatters';
import styles from './GeoPage.module.css';

interface Country { id: string; name: string; code: string; }
interface City { id: string; name: string; slug: string; country: string; country_name?: string; }
interface Area { id: string; name: string; city: string; city_name?: string; }
interface GeoLandmark { id: string; name: string; area: string; area_name?: string; gps?: GeoJSONPoint; }

type NodeType = 'country' | 'city' | 'area' | 'landmark';
type DrawerMode = 'country' | 'city' | 'area' | 'landmark' | null;

const editCountrySchema = z.object({
  name: z.string().min(1, 'Name is required'),
  code: z.string().length(2, 'Code must be exactly 2 characters').toUpperCase(),
});
const editCitySchema = z.object({
  name: z.string().min(1, 'Name is required'),
  country: z.string().min(1, 'Country is required'),
});
const editAreaSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  city: z.string().min(1, 'City is required'),
});
const editLandmarkSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  area: z.string().min(1, 'Area is required'),
});

type EditCountryForm = z.infer<typeof editCountrySchema>;
type EditCityForm = z.infer<typeof editCitySchema>;
type EditAreaForm = z.infer<typeof editAreaSchema>;
type EditLandmarkForm = z.infer<typeof editLandmarkSchema>;

const countrySchema = z.object({
  name: z.string().min(1, 'Name is required'),
  code: z.string().length(2, 'Code must be exactly 2 characters').toUpperCase(),
});
const citySchema = z.object({
  name: z.string().min(1, 'Name is required'),
  country: z.string().min(1, 'Country is required'),
});
const areaSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  city: z.string().min(1, 'City is required'),
});
const landmarkSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  area: z.string().min(1, 'Area is required'),
});

type CountryForm = z.infer<typeof countrySchema>;
type CityForm = z.infer<typeof citySchema>;
type AreaForm = z.infer<typeof areaSchema>;
type LandmarkForm = z.infer<typeof landmarkSchema>;

interface SelectedNode { type: NodeType; id: string; }

interface GeoDetailPanelProps {
  selected: SelectedNode;
  countries: Country[];
  cities: City[];
  areas: Area[];
  landmarks: GeoLandmark[];
  countryOptions: Array<{ value: string; label: string }>;
  cityOptions: Array<{ value: string; label: string }>;
  areaOptions: Array<{ value: string; label: string }>;
  editCountryForm: ReturnType<typeof useForm<EditCountryForm>>;
  editCityForm: ReturnType<typeof useForm<EditCityForm>>;
  editAreaForm: ReturnType<typeof useForm<EditAreaForm>>;
  editLandmarkForm: ReturnType<typeof useForm<EditLandmarkForm>>;
  editLandmarkGps: GeoJSONPoint | null;
  setEditLandmarkGps: (gps: GeoJSONPoint | null) => void;
  updateCountry: ReturnType<typeof useMutation<unknown, unknown, { id: string; data: EditCountryForm }>>;
  updateCity: ReturnType<typeof useMutation<unknown, unknown, { id: string; data: EditCityForm }>>;
  updateArea: ReturnType<typeof useMutation<unknown, unknown, { id: string; data: EditAreaForm }>>;
  updateLandmark: ReturnType<typeof useMutation<unknown, unknown, { id: string; data: EditLandmarkForm & { gps?: GeoJSONPoint } }>>;
  onDelete: () => void;
}

function GeoDetailPanel({
  selected,
  countries,
  cities,
  areas,
  landmarks,
  countryOptions,
  cityOptions,
  areaOptions,
  editCountryForm,
  editCityForm,
  editAreaForm,
  editLandmarkForm,
  editLandmarkGps,
  setEditLandmarkGps,
  updateCountry,
  updateCity,
  updateArea,
  updateLandmark,
  onDelete,
}: GeoDetailPanelProps) {
  const { type, id } = selected;

  const country = countries.find((c) => c.id === id);
  const city = cities.find((c) => c.id === id);
  const area = areas.find((a) => a.id === id);
  const landmark = landmarks.find((l) => l.id === id);

  const iconMap: Record<NodeType, React.ReactNode> = {
    country: <Globe size={18} strokeWidth={1.5} />,
    city: <Building2 size={18} strokeWidth={1.5} />,
    area: <Map size={18} strokeWidth={1.5} />,
    landmark: <Landmark size={18} strokeWidth={1.5} />,
  };

  return (
    <div className={styles.detailContent}>
      <div className={styles.detailHeader}>
        <span className={styles.detailIcon} aria-hidden="true">{iconMap[type]}</span>
        <div>
          <p className={styles.detailType}>{formatLabel(type)}</p>
          <p className={styles.detailId}>ID: {id}</p>
        </div>
        <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER']}>
          <Button
            variant="ghost"
            size="compact"
            aria-label="Delete"
            onClick={onDelete}
          >
            <Trash2 size={14} strokeWidth={1.5} />
          </Button>
        </RoleGate>
      </div>

      <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER']}>
        <>
          {type === 'country' && country && (
            <form
              className={styles.detailForm}
              onSubmit={editCountryForm.handleSubmit((d) =>
                updateCountry.mutate({ id, data: d })
              )}
            >
              <Input
                id="edit-country-name"
                label="Country name"
                required
                defaultValue={country.name}
                error={editCountryForm.formState.errors.name?.message}
                {...editCountryForm.register('name')}
              />
              <Input
                id="edit-country-code"
                label="Country code (2 chars)"
                required
                defaultValue={country.code}
                maxLength={2}
                error={editCountryForm.formState.errors.code?.message}
                {...editCountryForm.register('code')}
              />
              <div className={styles.detailFormActions}>
                <Button
                  type="submit"
                  variant="primary"
                  size="compact"
                  loading={updateCountry.isPending}
                  leftIcon={<Save size={14} strokeWidth={1.5} />}
                >
                  Save Changes
                </Button>
              </div>
            </form>
          )}

          {type === 'city' && city && (
            <form
              className={styles.detailForm}
              onSubmit={editCityForm.handleSubmit((d) =>
                updateCity.mutate({ id, data: d })
              )}
            >
              <Input
                id="edit-city-name"
                label="City name"
                required
                defaultValue={city.name}
                error={editCityForm.formState.errors.name?.message}
                {...editCityForm.register('name')}
              />
              <Select
                id="edit-city-country"
                label="Country"
                required
                options={countryOptions}
                defaultValue={city.country}
                error={editCityForm.formState.errors.country?.message}
                {...editCityForm.register('country')}
              />
              <div className={styles.detailFormActions}>
                <Button
                  type="submit"
                  variant="primary"
                  size="compact"
                  loading={updateCity.isPending}
                  leftIcon={<Save size={14} strokeWidth={1.5} />}
                >
                  Save Changes
                </Button>
              </div>
            </form>
          )}

          {type === 'area' && area && (
            <form
              className={styles.detailForm}
              onSubmit={editAreaForm.handleSubmit((d) =>
                updateArea.mutate({ id, data: d })
              )}
            >
              <Input
                id="edit-area-name"
                label="Area name"
                required
                defaultValue={area.name}
                error={editAreaForm.formState.errors.name?.message}
                {...editAreaForm.register('name')}
              />
              <Select
                id="edit-area-city"
                label="City"
                required
                options={cityOptions}
                defaultValue={area.city}
                error={editAreaForm.formState.errors.city?.message}
                {...editAreaForm.register('city')}
              />
              <div className={styles.detailFormActions}>
                <Button
                  type="submit"
                  variant="primary"
                  size="compact"
                  loading={updateArea.isPending}
                  leftIcon={<Save size={14} strokeWidth={1.5} />}
                >
                  Save Changes
                </Button>
              </div>
            </form>
          )}

          {type === 'landmark' && landmark && (
            <form
              className={styles.detailForm}
              onSubmit={editLandmarkForm.handleSubmit((d) =>
                updateLandmark.mutate({
                  id,
                  data: editLandmarkGps ? { ...d, gps: editLandmarkGps } : d,
                })
              )}
            >
              <Input
                id="edit-lm-name"
                label="Landmark name"
                required
                defaultValue={landmark.name}
                error={editLandmarkForm.formState.errors.name?.message}
                {...editLandmarkForm.register('name')}
              />
              <Select
                id="edit-lm-area"
                label="Area"
                required
                options={areaOptions}
                defaultValue={landmark.area}
                error={editLandmarkForm.formState.errors.area?.message}
                {...editLandmarkForm.register('area')}
              />
              <GPSInput
                id="edit-lm-gps"
                label="GPS Location"
                value={editLandmarkGps ?? landmark.gps ?? null}
                onChange={setEditLandmarkGps}
              />
              {(editLandmarkGps ?? landmark.gps) && (
                <div className={styles.mapPreview}>
                  <GPSMap
                    point={(editLandmarkGps ?? landmark.gps)!}
                    draggable
                    onDrag={([lat, lng]) =>
                      setEditLandmarkGps({ type: 'Point', coordinates: [lng, lat] })
                    }
                    height="200px"
                    zoom={14}
                  />
                </div>
              )}
              <div className={styles.detailFormActions}>
                <Button
                  type="submit"
                  variant="primary"
                  size="compact"
                  loading={updateLandmark.isPending}
                  leftIcon={<Save size={14} strokeWidth={1.5} />}
                >
                  Save Changes
                </Button>
              </div>
            </form>
          )}
        </>
      </RoleGate>

      {/* Read-only info for non-editors */}
      {type === 'landmark' && landmark && !landmark.gps && (
        <p className={styles.noGps}>No GPS coordinates recorded for this landmark.</p>
      )}
    </div>
  );
}

export default function GeoPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [selected, setSelected] = useState<SelectedNode | null>(null);
  const [drawerMode, setDrawerMode] = useState<DrawerMode>(null);
  const [landmarkGps, setLandmarkGps] = useState<GeoJSONPoint | null>(null);
  const [editLandmarkGps, setEditLandmarkGps] = useState<GeoJSONPoint | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  const { data: countries, isLoading: loadingCountries } = useQuery({
    queryKey: queryKeys.geo.countries(),
    queryFn: () => apiClient.get<{ data: Country[] }>('/api/v1/geo/countries/').then(r => r.data.data),
  });
  const { data: cities } = useQuery({
    queryKey: queryKeys.geo.cities(),
    queryFn: () => apiClient.get<{ data: City[] }>('/api/v1/geo/cities/').then(r => r.data.data),
  });
  const { data: areas } = useQuery({
    queryKey: queryKeys.geo.areas(),
    queryFn: () => apiClient.get<{ data: Area[] }>('/api/v1/geo/areas/').then(r => r.data.data),
  });
  const { data: landmarks } = useQuery({
    queryKey: queryKeys.geo.landmarks(),
    queryFn: () => apiClient.get<{ data: GeoLandmark[] }>('/api/v1/geo/landmarks/').then(r => r.data.data),
  });

  const countryForm = useForm<CountryForm>({ resolver: zodResolver(countrySchema) });
  const cityForm = useForm<CityForm>({ resolver: zodResolver(citySchema) });
  const areaForm = useForm<AreaForm>({ resolver: zodResolver(areaSchema) });
  const landmarkForm = useForm<LandmarkForm>({ resolver: zodResolver(landmarkSchema) });

  const editCountryForm = useForm<EditCountryForm>({ resolver: zodResolver(editCountrySchema) });
  const editCityForm = useForm<EditCityForm>({ resolver: zodResolver(editCitySchema) });
  const editAreaForm = useForm<EditAreaForm>({ resolver: zodResolver(editAreaSchema) });
  const editLandmarkForm = useForm<EditLandmarkForm>({ resolver: zodResolver(editLandmarkSchema) });

  const invalidateAll = () => {
    void qc.invalidateQueries({ queryKey: queryKeys.geo.countries() });
    void qc.invalidateQueries({ queryKey: queryKeys.geo.cities() });
    void qc.invalidateQueries({ queryKey: queryKeys.geo.areas() });
    void qc.invalidateQueries({ queryKey: queryKeys.geo.landmarks() });
  };

  const createCountry = useMutation({
    mutationFn: (d: CountryForm) => apiClient.post('/api/v1/geo/countries/', d),
    onSuccess: () => { toast.success('Country created'); setDrawerMode(null); countryForm.reset(); invalidateAll(); },
  });
  const createCity = useMutation({
    mutationFn: (d: CityForm) => apiClient.post('/api/v1/geo/cities/', d),
    onSuccess: () => { toast.success('City created'); setDrawerMode(null); cityForm.reset(); invalidateAll(); },
  });
  const createArea = useMutation({
    mutationFn: (d: AreaForm) => apiClient.post('/api/v1/geo/areas/', d),
    onSuccess: () => { toast.success('Area created'); setDrawerMode(null); areaForm.reset(); invalidateAll(); },
  });
  const createLandmark = useMutation({
    mutationFn: (d: LandmarkForm & { gps?: GeoJSONPoint }) => apiClient.post('/api/v1/geo/landmarks/', d),
    onSuccess: () => { toast.success('Landmark created'); setDrawerMode(null); landmarkForm.reset(); setLandmarkGps(null); invalidateAll(); },
  });

  const updateCountry = useMutation({
    mutationFn: ({ id, data }: { id: string; data: EditCountryForm }) =>
      apiClient.patch(`/api/v1/geo/countries/${id}/`, data),
    onSuccess: () => { toast.success('Country updated'); invalidateAll(); },
    onError: () => toast.error('Failed to update country'),
  });
  const updateCity = useMutation({
    mutationFn: ({ id, data }: { id: string; data: EditCityForm }) =>
      apiClient.patch(`/api/v1/geo/cities/${id}/`, data),
    onSuccess: () => { toast.success('City updated'); invalidateAll(); },
    onError: () => toast.error('Failed to update city'),
  });
  const updateArea = useMutation({
    mutationFn: ({ id, data }: { id: string; data: EditAreaForm }) =>
      apiClient.patch(`/api/v1/geo/areas/${id}/`, data),
    onSuccess: () => { toast.success('Area updated'); invalidateAll(); },
    onError: () => toast.error('Failed to update area'),
  });
  const updateLandmark = useMutation({
    mutationFn: ({ id, data }: { id: string; data: EditLandmarkForm & { gps?: GeoJSONPoint } }) =>
      apiClient.patch(`/api/v1/geo/landmarks/${id}/`, data),
    onSuccess: () => { toast.success('Landmark updated'); invalidateAll(); },
    onError: () => toast.error('Failed to update landmark'),
  });
  const deleteNode = useMutation({
    mutationFn: ({ type, id }: { type: NodeType; id: string }) => {
      const urlMap: Record<NodeType, string> = {
        country: `/api/v1/geo/countries/${id}/`,
        city: `/api/v1/geo/cities/${id}/`,
        area: `/api/v1/geo/areas/${id}/`,
        landmark: `/api/v1/geo/landmarks/${id}/`,
      };
      return apiClient.delete(urlMap[type]);
    },
    onSuccess: () => {
      toast.success('Deleted successfully');
      setSelected(null);
      setDeleteConfirmOpen(false);
      invalidateAll();
    },
    onError: () => toast.error('Failed to delete'),
  });

  function buildLandmarkPayload(d: LandmarkForm): LandmarkForm & { gps?: GeoJSONPoint } {
    if (landmarkGps !== null) return { ...d, gps: landmarkGps };
    return d;
  }

  function toggleExpand(id: string) {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  }

  const countryOptions = (countries ?? []).map(c => ({ value: c.id, label: `${c.name} (${c.code})` }));
  const cityOptions = (cities ?? []).map(c => ({ value: c.id, label: c.name }));
  const areaOptions = (areas ?? []).map(a => ({ value: a.id, label: a.name }));

  return (
    <AdminLayout title="Geographic Management">
      <PageHeader
        heading="Geographic Management"
        subheading="Countries, cities, areas and landmarks"
        actions={
          <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER']}>
            <div className={styles.headerActions}>
              <Button variant="secondary" size="compact" leftIcon={<Plus size={14} />} onClick={() => setDrawerMode('country')}>Country</Button>
              <Button variant="secondary" size="compact" leftIcon={<Plus size={14} />} onClick={() => setDrawerMode('city')}>City</Button>
              <Button variant="secondary" size="compact" leftIcon={<Plus size={14} />} onClick={() => setDrawerMode('area')}>Area</Button>
              <Button variant="primary" size="compact" leftIcon={<Plus size={14} />} onClick={() => setDrawerMode('landmark')}>Landmark</Button>
            </div>
          </RoleGate>
        }
      />

      <div className={styles.layout}>
        <nav className={styles.tree} aria-label="Geographic hierarchy">
          {loadingCountries ? (
            <SkeletonTable rows={4} columns={1} showHeader={false} />
          ) : (
            <ul className={styles.treeList}>
              {(countries ?? []).map(country => {
                const countryCities = (cities ?? []).filter(c => c.country === country.id);
                const isExpanded = expanded[country.id] ?? false;
                return (
                  <li key={country.id}>
                    <button
                      className={[styles.treeNode, selected?.id === country.id ? styles.treeNodeActive : ''].join(' ')}
                      onClick={() => { toggleExpand(country.id); setSelected({ type: 'country', id: country.id }); }}
                      aria-expanded={isExpanded}
                    >
                      {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      <Globe size={14} aria-hidden="true" />
                      <span>{country.name}</span>
                      <span className={styles.treeCode}>{country.code}</span>
                    </button>
                    {isExpanded && (
                      <ul className={styles.treeList}>
                        {countryCities.map(city => {
                          const cityAreas = (areas ?? []).filter(a => a.city === city.id);
                          const cityExpanded = expanded[city.id] ?? false;
                          return (
                            <li key={city.id} className={styles.treeIndent}>
                              <button
                                className={[styles.treeNode, selected?.id === city.id ? styles.treeNodeActive : ''].join(' ')}
                                onClick={() => { toggleExpand(city.id); setSelected({ type: 'city', id: city.id }); }}
                                aria-expanded={cityExpanded}
                              >
                                {cityExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                <Building2 size={14} aria-hidden="true" />
                                <span>{city.name}</span>
                              </button>
                              {cityExpanded && (
                                <ul className={styles.treeList}>
                                  {cityAreas.map(area => {
                                    const areaLandmarks = (landmarks ?? []).filter(l => l.area === area.id);
                                    const areaExpanded = expanded[area.id] ?? false;
                                    return (
                                      <li key={area.id} className={styles.treeIndent}>
                                        <button
                                          className={[styles.treeNode, selected?.id === area.id ? styles.treeNodeActive : ''].join(' ')}
                                          onClick={() => { toggleExpand(area.id); setSelected({ type: 'area', id: area.id }); }}
                                          aria-expanded={areaExpanded}
                                        >
                                          {areaExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                          <Map size={14} aria-hidden="true" />
                                          <span>{area.name}</span>
                                        </button>
                                        {areaExpanded && (
                                          <ul className={styles.treeList}>
                                            {areaLandmarks.map(lm => (
                                              <li key={lm.id} className={styles.treeIndent}>
                                                <button
                                                  className={[styles.treeNode, selected?.id === lm.id ? styles.treeNodeActive : ''].join(' ')}
                                                  onClick={() => setSelected({ type: 'landmark', id: lm.id })}
                                                >
                                                  <Landmark size={14} aria-hidden="true" />
                                                  <span>{lm.name}</span>
                                                </button>
                                              </li>
                                            ))}
                                          </ul>
                                        )}
                                      </li>
                                    );
                                  })}
                                </ul>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </nav>

        <div className={styles.detail}>
          {selected === null ? (
            <div className={styles.emptyDetail}>
              <Globe size={40} strokeWidth={1} aria-hidden="true" />
              <p>Select a location from the tree to view details</p>
            </div>
          ) : (
            <GeoDetailPanel
              selected={selected}
              countries={countries ?? []}
              cities={cities ?? []}
              areas={areas ?? []}
              landmarks={landmarks ?? []}
              countryOptions={countryOptions}
              cityOptions={cityOptions}
              areaOptions={areaOptions}
              editCountryForm={editCountryForm}
              editCityForm={editCityForm}
              editAreaForm={editAreaForm}
              editLandmarkForm={editLandmarkForm}
              editLandmarkGps={editLandmarkGps}
              setEditLandmarkGps={setEditLandmarkGps}
              updateCountry={updateCountry}
              updateCity={updateCity}
              updateArea={updateArea}
              updateLandmark={updateLandmark}
              onDelete={() => setDeleteConfirmOpen(true)}
            />
          )}
        </div>
      </div>

      {/* Delete Confirmation */}
      <Modal
        isOpen={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        title={`Delete ${selected?.type ?? ''}`}
        description="This action cannot be undone. The record will be soft-deleted."
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteConfirmOpen(false)}>Cancel</Button>
            <Button
              variant="destructive"
              loading={deleteNode.isPending}
              onClick={() => selected && deleteNode.mutate({ type: selected.type, id: selected.id })}
            >
              Delete
            </Button>
          </>
        }
      >
        <p className={styles.deleteWarning}>Are you sure you want to delete this {selected?.type}?</p>
      </Modal>

      {/* Create Country Drawer */}
      <Drawer isOpen={drawerMode === 'country'} onClose={() => setDrawerMode(null)} title="Add Country"
        footer={
          <Button variant="primary" loading={createCountry.isPending}
            onClick={countryForm.handleSubmit(d => createCountry.mutate(d))}>
            Create Country
          </Button>
        }>
        <form className={styles.drawerForm} onSubmit={countryForm.handleSubmit(d => createCountry.mutate(d))}>
          <Input id="country-name" label="Country name" required error={countryForm.formState.errors.name?.message} {...countryForm.register('name')} />
          <Input id="country-code" label="Country code (2 chars)" required error={countryForm.formState.errors.code?.message} maxLength={2} {...countryForm.register('code')} />
        </form>
      </Drawer>

      {/* Create City Drawer */}
      <Drawer isOpen={drawerMode === 'city'} onClose={() => setDrawerMode(null)} title="Add City"
        footer={
          <Button variant="primary" loading={createCity.isPending}
            onClick={cityForm.handleSubmit(d => createCity.mutate(d))}>
            Create City
          </Button>
        }>
        <form className={styles.drawerForm} onSubmit={cityForm.handleSubmit(d => createCity.mutate(d))}>
          <Input id="city-name" label="City name" required error={cityForm.formState.errors.name?.message} {...cityForm.register('name')} />
          <Select id="city-country" label="Country" required options={countryOptions} placeholder="Select country…"
            error={cityForm.formState.errors.country?.message} {...cityForm.register('country')} />
        </form>
      </Drawer>

      {/* Create Area Drawer */}
      <Drawer isOpen={drawerMode === 'area'} onClose={() => setDrawerMode(null)} title="Add Area"
        footer={
          <Button variant="primary" loading={createArea.isPending}
            onClick={areaForm.handleSubmit(d => createArea.mutate(d))}>
            Create Area
          </Button>
        }>
        <form className={styles.drawerForm} onSubmit={areaForm.handleSubmit(d => createArea.mutate(d))}>
          <Input id="area-name" label="Area name" required error={areaForm.formState.errors.name?.message} {...areaForm.register('name')} />
          <Select id="area-city" label="City" required options={cityOptions} placeholder="Select city…"
            error={areaForm.formState.errors.city?.message} {...areaForm.register('city')} />
        </form>
      </Drawer>

      {/* Create Landmark Drawer */}
      <Drawer isOpen={drawerMode === 'landmark'} onClose={() => setDrawerMode(null)} title="Add Landmark"
        footer={
          <Button variant="primary" loading={createLandmark.isPending}
            onClick={landmarkForm.handleSubmit(d => createLandmark.mutate(buildLandmarkPayload(d)))}>
            Create Landmark
          </Button>
        }>
        <form className={styles.drawerForm} onSubmit={landmarkForm.handleSubmit(d => createLandmark.mutate(buildLandmarkPayload(d)))}>
          <Input id="lm-name" label="Landmark name" required error={landmarkForm.formState.errors.name?.message} {...landmarkForm.register('name')} />
          <Select id="lm-area" label="Area" required options={areaOptions} placeholder="Select area…"
            error={landmarkForm.formState.errors.area?.message} {...landmarkForm.register('area')} />
          <GPSInput id="lm-gps" label="GPS Location" value={landmarkGps} onChange={setLandmarkGps} />
        </form>
      </Drawer>
    </AdminLayout>
  );
}
