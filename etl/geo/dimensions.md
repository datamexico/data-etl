# Data México Dimensión Geografía

The National Institute of Statistics and Geography (INEGI) provides the Unique Catalog of IDs of Geostatistical, State, Municipal and Local Areas through its official website. For reference the original files can be found here:
- [https://www.inegi.org.mx/app/ageeml/](https://www.inegi.org.mx/app/ageeml/) (Using the April 2019 standard)

This standard is used as the reference for the construction of all shared Geography Dimensions in DataMéxico. However, to ensure a good performance of the site, the IDs must following two criteria:

- Be integer numbers
- There must not be two identical identifiers, unless these belong to a different depth level (ie, there municipality ID must be different to entity ID or location ID)

We preprocessed the INEGI IDs, using the following methodology:

Federal Entity (`ent_id`): 
- The ID is maintained from `CVE_ENT`.

Municipality (`mun_id`): 
- The `CVE_MUN` is formatted, in such a way that always it has a 3-digit length, prefixing zeros (i.e, if `CVE_MUN` is `1`, the ID will be `001`).
- To the previously formatted ID, we prefixing it the `ent_id` appropiate.

Locality (`loc_id`):
- The `CVE_LOC` is formatted, in such a way that always it has a 3-digit length, prefixing zeros (i.e, if `CVE_LOC` is `2`, the ID will be `0002`).
- To the previously formatted ID, we prefixing it the `mun_id` appropiate.

Format:

| field | type | example |
| ---- | ---- | ---- |
| ent_id | `integer` | 1 |
| ent_name | `string` | Aguascalientes |
| mun_id | `integer` | 1001 |
| mun_name | `string` | Aguascalientes |
| loc_id | `integer` | 10010096 |
| loc_name | `string` | Agua Azul |

![Format ID](format_id.png)

Example:

| ent_id | ent_name | mun_id | mun_name | loc_id | loc_name |
| ---- | ---- | ---- | ---- | ---- | ---- |
| 1 | Aguascalientes | 1001 | Aguascalientes | 10010001 | Aguascalientes |
| 1 | Aguascalientes | 1001 | Aguascalientes | 10010094 | Granja Adelita |
| 1 | Aguascalientes | 1001 | Aguascalientes | 10010096 | Agua Azul |
| 1 | Aguascalientes | 1001 | Aguascalientes | 10010100 | Rancho Alegre |


You can find the ID list in [geo_mx.csv](geo_mx.csv).

We recommend that everyone who participates in the ETL process uses this standard for avoiding duplication of geographical dimensions.
