# 宿舍示意场景

净尺寸3.70×6.20×2.80米。房长由两端各2.10米的桌柜与高架床单元，加中段2.00米落地床推算。场景使用同一组参数化构件生成五个视角；记忆与照片只用于几何判断，照片不随数据提供。

阳台端有两扇磨砂窗和半玻璃半铝合金门。两窗净玻璃各0.495×1.085米，门上半净玻璃0.830×0.9975米，合计1.902075平方米。阳台门下半为古铜/香槟棕横向压纹铝合金板，框与门扇同色；入户门为米白橡木饰面金属造型门。材料颜色为视觉近似，不能据此确定太阳吸收率或传热系数。两台风扇仅为静态外观近似，未作运动机构或气流验证。

images目录内五张JPG供研究报告展示，宽1600像素；不参与热量、湿量和电量计算。参数入口为参数.json，构建和渲染脚本位于source目录，全部材质程序化生成，无照片贴图。

## 重建

需要Blender 4.2 LTS；已用4.2.23验证。将blender加入命令搜索路径，在研究目录执行：

```sh
blender --background --factory-startup --python scene/source/build_model.py
blender --background scene/dormitory.blend --python scene/source/validate_model.py
blender --background scene/dormitory.blend --python scene/source/check_balcony_glazing.py
blender --background scene/dormitory.blend --python scene/source/render_model.py -- final
uv run --frozen python scene/prepare_images.py
```

构建命令生成scene/dormitory.blend和model_index.json，渲染命令生成scene/renders中的五张PNG。生成的blend不随源码提供；上述构建命令可重建同一场景。几何、装配、门窗面积与单视角渲染命令均已验证。默认CPU渲染；在支持Metal的设备上，可在final后追加--metal使用GPU。剖面和侧视仅切换显示，不移动家具。渲染灯光为外观近似，不提供照度或热边界条件。
