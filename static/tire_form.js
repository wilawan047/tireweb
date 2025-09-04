console.log('tire_form.js loaded');

// ฟังก์ชันสำหรับการแสดง preview รูปภาพ
function setupImagePreview() {
    console.log('setupImagePreview called');
    const fileInput = document.querySelector('input[name="tire_image"]');
    console.log('fileInput found:', fileInput);
    
    if (fileInput) {
        // หา upload area ที่มี class border-2 border-dashed
        const uploadArea = fileInput.closest('.border-2.border-dashed');
        console.log('uploadArea found:', uploadArea);
        
        if (uploadArea) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // สร้าง preview รูปภาพ
                const reader = new FileReader();
                reader.onload = function(e) {
                    // ลบ preview เดิม (ถ้ามี)
                    const existingPreview = uploadArea.querySelector('.image-preview');
                    if (existingPreview) {
                        existingPreview.remove();
                    }
                    
                    // สร้าง preview ใหม่
                    const previewDiv = document.createElement('div');
                    previewDiv.className = 'image-preview mt-4';
                    previewDiv.innerHTML = `
                        <img src="${e.target.result}" alt="Preview" class="max-h-40 rounded shadow border mx-auto">
                        <p class="text-sm text-gray-600 mt-2 text-center">${file.name}</p>
                    `;
                    
                    // เพิ่ม preview ลงใน upload area (เฉพาะส่วนอัปโหลด)
                    uploadArea.appendChild(previewDiv);
                };
                reader.readAsDataURL(file);
            }
        });
        
        // เพิ่ม drag and drop functionality
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('border-indigo-400', 'bg-indigo-50');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('border-indigo-400', 'bg-indigo-50');
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('border-indigo-400', 'bg-indigo-50');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                fileInput.dispatchEvent(new Event('change'));
            }
        });
        }
    }
}

// Static data for dropdowns (if no data from API)
const WIDTHS = ["135","145","155","165","175","185","195","205","215","225","235","245","255","265","275","285","295","305","315"];
const ASPECTS = ["30","35","40","45","50","55","60","65","70","75","80","85"];
const RIM_DIAMETERS = ["13","14","15","16","17","18","19","20","21","22"];

function setDropdownOptions(select, options, selectedValue) {
    select.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'ไม่ระบุ';
    select.appendChild(opt);
    options.forEach(val => {
        const o = document.createElement('option');
        if (typeof val === 'object') {
            o.value = val.value;
            o.textContent = val.label;
            if (selectedValue && selectedValue == val.value) o.selected = true;
        } else {
            o.value = val;
            o.textContent = val;
            if (selectedValue && selectedValue == val) o.selected = true;
        }
        select.appendChild(o);
    });
}

async function loadBrands(selectedBrandId) {
    const res = await fetch('/api/brands');
    const brands = await res.json();
    const brandSelect = document.getElementById('brandSelect');
    brandSelect.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'ไม่ระบุ';
    brandSelect.appendChild(opt);
    brands.forEach(b => {
        const o = document.createElement('option');
        o.value = b.brand_id;
        o.textContent = b.brand_name;
        if (selectedBrandId && String(selectedBrandId) === String(b.brand_id)) o.selected = true;
        brandSelect.appendChild(o);
    });
}

async function loadModels(brandId, selectedModelId) {
    const res = await fetch('/api/tire_models');
    const models = await res.json();
    const modelSelect = document.getElementById('modelSelect');
    modelSelect.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'ไม่ระบุ';
    modelSelect.appendChild(opt);
    models.filter(m => !brandId || m.brand_id == brandId).forEach(m => {
        const o = document.createElement('option');
        o.value = m.model_id;
        o.textContent = m.model_name;
        if (selectedModelId && selectedModelId == m.model_id) o.selected = true;
        modelSelect.appendChild(o);
    });
}

async function loadOptions(modelId, tire) {
    const res = await fetch('/api/tire_options?model_id=' + (modelId || ''));
    const opts = await res.json();
    setDropdownOptions(document.getElementById('widthSelect'), opts.width.length ? opts.width : WIDTHS, tire?.width);
    setDropdownOptions(document.getElementById('aspectRatioSelect'), opts.aspect_ratio.length ? opts.aspect_ratio : ASPECTS, tire?.aspect_ratio);
    setDropdownOptions(document.getElementById('rimDiameterSelect'), opts.rim_diameter.length ? opts.rim_diameter : RIM_DIAMETERS, tire?.rim_diameter);
    // Preselect for construction, speed_symbol, ply_rating, tubeless_type, tire_load_type
    if (tire) {
        document.getElementById('constructionSelect').value = tire.construction || '';
        document.getElementById('speedSymbolSelect').value = tire.speed_symbol || '';
        document.getElementById('plyRatingSelect').value = tire.ply_rating || '';
        document.getElementById('tubelessTypeSelect').value = tire.tubeless_type || '';
        document.getElementById('tireLoadTypeSelect').value = tire.tire_load_type || '';
        // Checkbox for service_description (XL)
        document.querySelector('input[name="service_description"]').checked = tire.service_description === 'XL';
        // Checkbox for high_speed_rating
        document.querySelector('input[name="high_speed_rating"]').checked = !!tire.high_speed_rating;
    }
}

function safeValue(val) {
    return (val === undefined || val === null || val === "None") ? "" : val;
}

// ฟังก์ชันสำหรับ customer_form.html: อัปเดตรุ่นตามยี่ห้อที่เลือก
async function updateVehicleModelDropdown(vehicleId) {
  const brandSelect = document.getElementById('brand_' + vehicleId);
  const modelSelect = document.getElementById('model_' + vehicleId);
  const selectedBrandId = brandSelect.value;
  const selectedModelId = modelSelect.getAttribute('data-selected') || modelSelect.value;
  // ลบ option เดิม
  while (modelSelect.options.length > 1) modelSelect.remove(1);
  if (!selectedBrandId) return;
  // ดึงข้อมูลรุ่นจาก API
  const res = await fetch('/api/vehicle_models?brand_id=' + selectedBrandId);
  const models = await res.json();
  models.forEach(function(m) {
    const opt = document.createElement('option');
    opt.value = m.model_id;
    opt.textContent = m.model_name;
    if (selectedModelId && selectedModelId == m.model_id) opt.selected = true;
    modelSelect.appendChild(opt);
  });
}

// โหลด models ทั้งหมดจาก data attribute หรือ AJAX
window.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.vehicle-brand').forEach(function(brandSelect) {
    brandSelect.addEventListener('change', function() {
      const vehicleId = this.getAttribute('data-vehicle-id');
      updateVehicleModelDropdown(vehicleId);
    });
    // โหลดรุ่นอัตโนมัติเมื่อเปิดฟอร์ม (กรณี edit)
    const vehicleId = brandSelect.getAttribute('data-vehicle-id');
    const modelSelect = document.getElementById('model_' + vehicleId);
    if (brandSelect.value && modelSelect && (modelSelect.getAttribute('data-selected') || modelSelect.value)) {
      updateVehicleModelDropdown(vehicleId);
    }
  });
});

document.addEventListener('DOMContentLoaded', async function() {
    let tire = window.tireData || null;
    let brandId = tire?.brand_id;
    
    // Setup image preview functionality
    setupImagePreview();
    
    // If brand_id is missing but model_id exists, lookup brand_id from model_id
    if (!brandId && tire?.model_id) {
        const res = await fetch('/api/tire_models');
        const models = await res.json();
        const found = models.find(m => String(m.model_id) === String(tire.model_id));
        if (found) brandId = found.brand_id;
    }
    await loadBrands(safeValue(brandId));
    await loadModels(safeValue(brandId), safeValue(tire?.model_id));
    await loadOptions(safeValue(tire?.model_id), tire);

    // Preselect all dropdowns and checkboxes after all loads
    if (tire) {
        document.getElementById('brandSelect').value = safeValue(brandId);
        document.getElementById('modelSelect').value = safeValue(tire.model_id);
        document.getElementById('widthSelect').value = safeValue(tire.width);
        document.getElementById('aspectRatioSelect').value = safeValue(tire.aspect_ratio);
        document.getElementById('constructionSelect').value = safeValue(tire.construction);
        document.getElementById('rimDiameterSelect').value = safeValue(tire.rim_diameter);
        document.getElementById('speedSymbolSelect').value = safeValue(tire.speed_symbol);
        document.getElementById('plyRatingSelect').value = safeValue(tire.ply_rating);
        document.getElementById('tubelessTypeSelect').value = safeValue(tire.tubeless_type);
        document.getElementById('tireLoadTypeSelect').value = safeValue(tire.tire_load_type);
        document.querySelector('input[name="service_description"]').checked = tire.service_description === 'XL';
        document.querySelector('input[name="high_speed_rating"]').checked = !!tire.high_speed_rating;
        // For text/number fields
        document.querySelector('input[name="load_index"]').value = safeValue(tire.load_index);
        document.querySelector('input[name="price_each"]').value = safeValue(tire.price_each);
        document.querySelector('input[name="price_set"]').value = safeValue(tire.price_set);
        document.querySelector('input[name="product_date"]').value = safeValue(tire.product_date);
    }

    document.getElementById('brandSelect').addEventListener('change', async function() {
        // Store current values
        const prevModel = document.getElementById('modelSelect').value;
        const prevWidth = document.getElementById('widthSelect').value;
        const prevAspect = document.getElementById('aspectRatioSelect').value;
        const prevRim = document.getElementById('rimDiameterSelect').value;
        const prevConstruction = document.getElementById('constructionSelect').value;
        const prevSpeed = document.getElementById('speedSymbolSelect').value;
        const prevPly = document.getElementById('plyRatingSelect').value;
        const prevTubeless = document.getElementById('tubelessTypeSelect').value;
        const prevLoadType = document.getElementById('tireLoadTypeSelect').value;

        // Load models for new brand, try to keep previous model if possible
        await loadModels(this.value, prevModel);

        // Load options for the (possibly new) model, try to keep previous values
        await loadOptions(prevModel, {
            width: prevWidth,
            aspect_ratio: prevAspect,
            rim_diameter: prevRim,
            construction: prevConstruction,
            speed_symbol: prevSpeed,
            ply_rating: prevPly,
            tubeless_type: prevTubeless,
            tire_load_type: prevLoadType
        });
    });
    document.getElementById('modelSelect').addEventListener('change', async function() {
        // Store current values
        const prevWidth = document.getElementById('widthSelect').value;
        const prevAspect = document.getElementById('aspectRatioSelect').value;
        const prevRim = document.getElementById('rimDiameterSelect').value;
        const prevConstruction = document.getElementById('constructionSelect').value;
        const prevSpeed = document.getElementById('speedSymbolSelect').value;
        const prevPly = document.getElementById('plyRatingSelect').value;
        const prevTubeless = document.getElementById('tubelessTypeSelect').value;
        const prevLoadType = document.getElementById('tireLoadTypeSelect').value;

        await loadOptions(this.value, {
            width: prevWidth,
            aspect_ratio: prevAspect,
            rim_diameter: prevRim,
            construction: prevConstruction,
            speed_symbol: prevSpeed,
            ply_rating: prevPly,
            tubeless_type: prevTubeless,
            tire_load_type: prevLoadType
        });
    });

    var modelSelect = document.getElementById('modelSelect');
    if (modelSelect) {
        modelSelect.addEventListener('change', function() {
            var modelId = this.value;
            var yearSelect = document.getElementById('yearSelect');
            if (!yearSelect) return;
            yearSelect.innerHTML = '<option value="">ไม่ระบุ</option>';
            if (modelId) {
                fetch('/api/vehicle_model_years?model_id=' + encodeURIComponent(modelId))
                    .then(res => res.json())
                    .then(years => {
                        years.forEach(function(year) {
                            var opt = document.createElement('option');
                            opt.value = year;
                            opt.text = year;
                            yearSelect.appendChild(opt);
                        });
                    });
            }
        });
    }
}); 