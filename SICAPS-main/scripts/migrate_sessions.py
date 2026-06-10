from core.models import HistoriaClinica
from datetime import datetime
from pymongo import UpdateOne

coll = HistoriaClinica._get_collection()
updates = []
count_docs = 0
count_updated = 0
for raw in coll.find():
    count_docs += 1
    sesiones = raw.get('sesiones', [])
    if not sesiones:
        continue
    needs_update = False
    nuevas = []
    for s in sesiones:
        # detectar si tiene campos antiguos
        if any(k in s for k in ['motivo_consulta', 'fecha_sesion', 'diagnostico', 'observaciones', 'plan_tratamiento', 'profesional_id']):
            needs_update = True
        # If already in new format (has fecha_registro or codigo_diagnostico), keep as-is
        if 'fecha_registro' in s or 'codigo_diagnostico' in s or 'observaciones_clinicas' in s:
            nuevas.append(s)
            continue
        fecha = s.get('fecha_sesion') or s.get('fecha_registro') or datetime.now()
        if isinstance(fecha, str):
            try:
                fecha = datetime.fromisoformat(fecha)
            except Exception:
                fecha = datetime.now()
        nueva = {
            'codigo_diagnostico': s.get('diagnostico') or '',
            'nombre': s.get('diagnostico') or s.get('motivo_consulta') or '',
            'descripcion': s.get('observaciones') or '',
            'fecha_registro': fecha,
            'profesional_responsable': s.get('profesional_id') or s.get('profesional_responsable') or '',
            'observaciones_clinicas': s.get('observaciones') or s.get('observaciones_clinicas') or '',
            'nivel_riesgo': s.get('nivel_riesgo') or 'Bajo',
            'estado_paciente': s.get('estado_paciente') or 'Estable'
        }
        nuevas.append(nueva)
    if needs_update:
        updates.append(UpdateOne({'_id': raw['_id']}, {'$set': {'sesiones': nuevas}}))
        count_updated += 1

if updates:
    result = coll.bulk_write(updates)
    print('Migrated documents:', count_updated)
else:
    print('No documents needed migration')
print('Scanned documents:', count_docs)
