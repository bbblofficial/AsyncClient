package com.example.asyncmenus.core;

import net.minecraftforge.fml.relauncher.IFMLLoadingPlugin;

import java.util.Map;

@IFMLLoadingPlugin.MCVersion("1.8.9")
@IFMLLoadingPlugin.TransformerExclusions({"com.example.asyncmenus.core"})
public class AsyncMenusLoadingPlugin implements IFMLLoadingPlugin {

    @Override public String[] getASMTransformerClass() {
        return new String[]{ LoadingScreenTransformer.class.getName() };
    }
    @Override public String getModContainerClass()           { return null; }
    @Override public String getSetupClass()                  { return null; }
    @Override public void   injectData(Map<String,Object> d) {}
    @Override public String getAccessTransformerClass()      { return null; }
}
